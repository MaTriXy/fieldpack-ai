"""Demo replay engine for DEMO_MODE.

Loads pre-computed responses from demo/script.json and replays them
as WebSocket events with realistic timing. No LLM, Ollama, or ChromaDB
required — pure JSON playback for deterministic video recording.
"""

import asyncio
import json
import logging
import re
from pathlib import Path

from app.config import settings

_logger = logging.getLogger(__name__)

_script: dict | None = None


def _load_script() -> dict:
    """Load and cache the demo script JSON."""
    global _script
    if _script is not None:
        return _script

    script_path = Path(__file__).resolve().parent.parent / settings.demo_script_path
    if not script_path.exists():
        raise FileNotFoundError(f"Demo script not found: {script_path}")

    with open(script_path, encoding="utf-8") as f:
        _script = json.load(f)

    _logger.info("Demo script loaded: %s", script_path)
    return _script


def _pattern_matches(pattern: str, msg_lower: str) -> bool:
    """Whole-word (or whole-phrase) match, case-insensitive.

    Why: substring matching hits "hi" inside "this", which mis-routes the
    planting question to the greeting scene. Word boundaries stop that.
    """
    return re.search(rf"\b{re.escape(pattern.lower())}\b", msg_lower) is not None


def _match_scene(message: str, has_image: bool, scenes: list[dict]) -> dict | None:
    """Find the best matching scene for a user message.

    Matches by checking if any of the scene's match_patterns appear
    as whole words in the message (case-insensitive). If a scene requires
    an image (match_has_image=true), it only matches when has_image is true.
    Returns the first matching scene, or None.
    """
    msg_lower = message.lower()
    for scene in scenes:
        if scene.get("match_has_image") and not has_image:
            continue
        for pattern in scene.get("match_patterns", []):
            if _pattern_matches(pattern, msg_lower):
                return scene
    return None


def _match_mission_chat(message: str, scenes: list[dict]) -> dict | None:
    """Find matching mission chat scene."""
    msg_lower = message.lower()
    for scene in scenes:
        for pattern in scene.get("match_patterns", []):
            if _pattern_matches(pattern, msg_lower):
                return scene
    return None


# ------------------------------------------------------------------
# Field chat WebSocket replay
# ------------------------------------------------------------------

async def replay_field_chat_ws(websocket, message: str, image_path: str | None, msg: dict):
    """Replay a field chat scene over WebSocket.

    Produces the same event sequence as the real pipeline:
    status → pipeline_mode → pipeline_insight → node_stats → token → sources → answer_done → done
    """
    script = _load_script()
    scenes = script.get("field_chat", [])
    has_image = image_path is not None

    # Try to find image-specific scene first if we have an image
    scene = None
    if has_image:
        image_scenes = [s for s in scenes if s.get("match_has_image")]
        scene = _match_scene(message, True, image_scenes)
        # If image is present but no text pattern matched, use the first image scene
        if scene is None and image_scenes:
            scene = image_scenes[0]

    if scene is None:
        scene = _match_scene(message, has_image, scenes)

    if scene is None:
        scene = script.get("fallback", {})

    _logger.info("Demo replay: matched scene '%s'", scene.get("id", "fallback"))

    # Replay agent steps with timing
    agent_steps = scene.get("agent_steps", [])
    insights = {i["after_step"]: i for i in scene.get("pipeline_insights", [])}
    node_stats = scene.get("node_stats", [])
    node_stats_by_step = {}

    # Map node_stats to step names for lookup
    step_names_in_order = [s["step"] for s in agent_steps]
    stats_idx = 0
    for ns in node_stats:
        node_stats_by_step[ns["node"]] = ns

    # Map step names to node names (step label -> LangGraph node name)
    _STEP_TO_NODE = {
        "classifying": "classify_and_extract",
        "routing": "route_intent",
        "evaluating": "needs_search_node",
        "crafting": "craft_search_query",
        "searching": "execute_searches",
        "reranking": "rerank_results",
        "expanding": "expand_route_node",
        "generating": "generate_answer",
        "saving": "log_observation_node",
    }

    for i, step in enumerate(agent_steps):
        # Emit status event
        await websocket.send_json({
            "type": "status",
            "step": step["step"],
            "detail": step.get("detail", ""),
            "tool_calls_log_entry": None,
        })

        # Emit pipeline_mode after evaluating step
        if step["step"] == "evaluating":
            await asyncio.sleep(0.1)
            await websocket.send_json({
                "type": "pipeline_mode",
                "mode": scene.get("pipeline_mode", "rag"),
            })

        # Wait for the step's delay
        delay_s = step.get("delay_ms", 500) / 1000.0
        await asyncio.sleep(delay_s)

        # Emit pipeline insight if one follows this step
        if i in insights:
            insight = insights[i]
            await websocket.send_json({
                "type": "pipeline_insight",
                "node": insight["node"],
                "text": insight["text"],
            })

        # Emit node_complete + node_stats
        node_name = _STEP_TO_NODE.get(step["step"], step["step"])
        await websocket.send_json({
            "type": "node_complete",
            "node": node_name,
            "tool_calls_log_entry": {},
        })

        ns = node_stats_by_step.get(node_name)
        if ns:
            await websocket.send_json({
                "type": "node_stats",
                "node": ns["node"],
                "latency_ms": ns["latency_ms"],
                "model": ns.get("model"),
            })

    # Stream response tokens character by character
    response = scene.get("response", "")
    chars_per_sec = scene.get("stream_chars_per_sec", script.get("meta", {}).get("stream_chars_per_sec", 30))
    char_delay = 1.0 / chars_per_sec if chars_per_sec > 0 else 0.033

    # Stream in small chunks (3-5 chars) for realistic feel
    chunk_size = 3
    for j in range(0, len(response), chunk_size):
        chunk = response[j:j + chunk_size]
        await websocket.send_json({"type": "token", "content": chunk})
        await asyncio.sleep(char_delay * len(chunk))

    # Emit sources
    sources = scene.get("sources", [])
    if sources:
        await websocket.send_json({"type": "sources", "sources": sources})

    # Emit answer_done
    if response:
        await websocket.send_json({"type": "answer_done"})

    # Emit done event
    conversation_history = msg.get("conversation_history", [])
    conversation_history.append({"role": "user", "content": message})
    conversation_history.append({"role": "assistant", "content": response})

    await websocket.send_json({
        "type": "done",
        "final_answer": response,
        "conversation_history": conversation_history,
        "conversation_summary": f"User asked about {scene.get('id', 'topic')}. Assistant provided detailed answer.",
        "observation_stats": None,
        "tool_calls_log": [],
        "total_latency_ms": scene.get("total_latency_ms", 5000),
        "llm_calls": scene.get("llm_calls", 3),
        "model": "fieldpack-assistant-lite",
        "image_description": scene.get("image_description"),
    })


# ------------------------------------------------------------------
# Field chat HTTP replay
# ------------------------------------------------------------------

async def replay_field_chat_http(message: str, image_path: str | None) -> dict:
    """Return a pre-computed field chat response for the HTTP endpoint."""
    script = _load_script()
    scenes = script.get("field_chat", [])
    has_image = image_path is not None

    scene = None
    if has_image:
        image_scenes = [s for s in scenes if s.get("match_has_image")]
        scene = _match_scene(message, True, image_scenes)
    if scene is None:
        scene = _match_scene(message, has_image, scenes)
    if scene is None:
        scene = script.get("fallback", {})

    return {
        "reply": scene.get("response", ""),
        "conversation_history": [],
        "conversation_summary": "",
        "tool_calls_log": [],
        "sources": [
            {"title": s["title"], "score": s["score"]}
            for s in scene.get("sources", [])
        ],
        "observation_stats": None,
    }


# ------------------------------------------------------------------
# Mission chat replay
# ------------------------------------------------------------------

async def replay_mission_chat_ws(websocket, message: str):
    """Replay a mission chat scene over WebSocket."""
    script = _load_script()
    scenes = script.get("mission_chat", [])
    scene = _match_mission_chat(message, scenes)

    if scene is None:
        # Default to first mission scene
        scene = scenes[0] if scenes else {
            "reply": "I can help you prepare a Knowledge Pack. Where are you deploying to?",
            "mission_card": None,
        }

    await websocket.send_json({"type": "status", "step": "planning"})
    await asyncio.sleep(1.5)

    await websocket.send_json({
        "type": "done",
        "reply": scene["reply"],
        "mission_card": scene.get("mission_card"),
    })


async def replay_mission_chat_http(message: str) -> dict:
    """Return a pre-computed mission chat response for the HTTP endpoint."""
    script = _load_script()
    scenes = script.get("mission_chat", [])
    scene = _match_mission_chat(message, scenes)

    if scene is None:
        scene = scenes[0] if scenes else {
            "reply": "I can help you prepare a Knowledge Pack. Where are you deploying to?",
            "mission_card": None,
        }

    return {
        "reply": scene["reply"],
        "mission_card": scene.get("mission_card"),
    }


# ------------------------------------------------------------------
# Mission pipeline (agent farm) replay
# ------------------------------------------------------------------

async def replay_mission_pipeline_ws(websocket, crops: list[str], region: str):
    """Replay the mission build pipeline over WebSocket.

    Emits: status → phase_complete → stats → done events matching
    the AgentProgressPage frontend expectations.
    """
    script = _load_script()
    pipeline = script.get("mission_pipeline", {})
    steps = pipeline.get("steps", [])
    stats_updates = {u["after_step"]: u for u in pipeline.get("stats_updates", [])}
    done_summary = pipeline.get("done_summary", {})

    phase_start_times: dict[str, float] = {}
    import time

    for i, step in enumerate(steps):
        phase = step["phase"]
        if phase not in phase_start_times:
            phase_start_times[phase] = time.perf_counter()

        await websocket.send_json({
            "type": "status",
            "phase": phase,
            "detail": step["detail"],
        })

        delay_s = step.get("delay_ms", 2000) / 1000.0
        await asyncio.sleep(delay_s)

        # Check if next step is a different phase — if so, emit phase_complete
        next_phase = steps[i + 1]["phase"] if i + 1 < len(steps) else None
        if next_phase != phase:
            elapsed = time.perf_counter() - phase_start_times[phase]
            await websocket.send_json({
                "type": "phase_complete",
                "phase": phase,
                "latency_ms": round(elapsed * 1000),
            })

        # Emit stats update if scheduled after this step
        if i in stats_updates:
            su = stats_updates[i]
            await websocket.send_json({
                "type": "stats",
                "findings": su["findings"],
                "tables": su["tables"],
                "chunks": su["chunks"],
                "images": su["images"],
            })

    # Done
    await websocket.send_json({
        "type": "done",
        "summary": done_summary,
    })


# ------------------------------------------------------------------
# Pack / health stubs for demo mode
# ------------------------------------------------------------------

def get_demo_pack_info() -> dict:
    """Return a fake active pack for demo mode."""
    script = _load_script()
    return {
        "pack_id": "casamance_agriculture",
        "name": script.get("meta", {}).get("pack_name", "Casamance Agriculture Pack"),
        "region": "Casamance, Senegal",
        "crops": ["cassava", "rice", "maize", "groundnut", "tomato", "millet"],
        "knowledge_entries": 190,
        "sources": ["FAO", "IITA", "PlantVillage", "AfricaRice", "ICRISAT", "ISRA Senegal"],
        "version": "1.0.0",
    }
