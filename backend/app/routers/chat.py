import asyncio
import json
import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.agents.field_assistant import run_field_assistant, run_field_assistant_stream
from app.config import settings
from app.demo_replay import replay_field_chat_http, replay_field_chat_ws
from app.knowledge_pack.loader import get_active_pack
from app.tools.observation_log import log_observation

# Serialize pipeline runs — the singleton PipelineLogger is not safe
# for concurrent pipelines sharing the same session counters.
_pipeline_lock = asyncio.Lock()

router = APIRouter(prefix="/chat", tags=["chat"])
_logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096

# Rate limit: max 10 messages per 10-second window per WebSocket connection
_WS_RATE_LIMIT_MAX = 10
_WS_RATE_LIMIT_WINDOW = 10.0


class ChatMessage(BaseModel):
    message: str = Field(max_length=MAX_MESSAGE_LENGTH)
    image_path: str | None = None
    conversation_history: list[dict] = Field(default_factory=list, max_length=50)
    conversation_summary: str = ""
    session_id: str | None = None
    language: str | None = None


class SourceInfo(BaseModel):
    title: str
    score: float


class ChatResponse(BaseModel):
    reply: str
    conversation_history: list[dict] = Field(default_factory=list)
    conversation_summary: str = ""
    tool_calls_log: list[dict] = Field(default_factory=list)
    sources: list[SourceInfo] = Field(default_factory=list)
    observation_stats: dict | None = None


def _validate_image_path(image_path: str | None) -> str | None:
    """Validate image_path is within allowed directories.

    Uses posix-normalised resolved strings for comparison so that mixed
    forward/back-slash paths round-tripped from Windows clients compare equal.
    """
    if image_path is None:
        return None
    p = Path(image_path).resolve()
    p_str = p.as_posix()
    uploads_root_str = settings.uploads_path.resolve().as_posix() + "/"
    packs_root_str = settings.packs_path.resolve().as_posix() + "/"
    if not (p_str.startswith(uploads_root_str) or p_str.startswith(packs_root_str)):
        _logger.warning(
            "Image path rejected: p=%s uploads_root=%s packs_root=%s",
            p_str, uploads_root_str, packs_root_str,
        )
        raise HTTPException(status_code=400, detail="Invalid image path")
    if not p.is_file():
        raise HTTPException(status_code=400, detail="Image file not found")
    return str(p)


@router.post("/", response_model=ChatResponse)
async def chat(msg: ChatMessage):
    """Send a message to the field assistant (HTTP, non-streaming)."""
    if settings.demo_mode:
        result = await replay_field_chat_http(msg.message, msg.image_path)
        return ChatResponse(**result)

    pack = get_active_pack()
    if pack is None:
        raise HTTPException(
            status_code=503,
            detail="No Knowledge Pack is loaded. Load a pack first via POST /packs/load/{pack_id}.",
        )

    validated_image = _validate_image_path(msg.image_path)

    try:
        async with _pipeline_lock:
            result = await run_field_assistant(
                message=msg.message,
                image_path=validated_image,
                conversation_history=msg.conversation_history,
                conversation_summary=msg.conversation_summary,
                session_id=msg.session_id,
                language=msg.language,
            )
    except Exception as e:
        _logger.exception("Pipeline error")
        raise HTTPException(status_code=500, detail="Pipeline error. Check server logs.")

    ranked = result.get("ranked_results", [])
    sources = [
        SourceInfo(title=r.source, score=round(r.relevance_score, 3))
        for r in ranked if hasattr(r, "relevance_score")
    ]

    return ChatResponse(
        reply=result.get("final_answer", ""),
        conversation_history=result.get("conversation_history", []),
        conversation_summary=result.get("conversation_summary", ""),
        tool_calls_log=result.get("tool_calls_log", []),
        sources=sources,
        observation_stats=result.get("observation_stats"),
    )


class SaveToJournalRequest(BaseModel):
    messages: list[dict] = Field(..., min_length=1, max_length=100)
    image_path: str | None = None


class SaveToJournalResponse(BaseModel):
    observation_id: int
    summary: str


@router.post("/save-to-journal", response_model=SaveToJournalResponse)
def save_conversation_to_journal(body: SaveToJournalRequest):
    """Summarize a chat conversation and save it as a field observation."""
    pack = get_active_pack()
    if pack is None:
        raise HTTPException(503, "No Knowledge Pack loaded")

    # Build conversation text for the LLM
    conv_lines = []
    for m in body.messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if content:
            conv_lines.append(f"{role.upper()}: {content[:500]}")
    conv_text = "\n".join(conv_lines[-20:])  # last 20 messages max

    from langchain_core.messages import HumanMessage, SystemMessage
    from app.agents.models import extract_text
    from app.models.offline_llm import get_field_llm

    try:
        llm = get_field_llm(temperature=0.2, num_predict=256)
        response = llm.invoke([
            SystemMessage(content=(
                "Summarize this field conversation into a concise observation log entry "
                "for a humanitarian field worker's journal. Include: what was discussed, "
                "any diagnosis or findings, and recommended actions. "
                "Write in first person as if the field worker is logging it. "
                "Keep under 150 words. No markdown headings."
            )),
            HumanMessage(content=conv_text),
        ])
        summary = extract_text(response)
    except Exception:
        # Fallback: use last assistant message as the summary
        assistant_msgs = [m.get("content", "").strip() for m in body.messages if m.get("role") == "assistant" and m.get("content", "").strip()]
        summary = assistant_msgs[-1][:300] if assistant_msgs else "Chat conversation logged."

    # Determine observation type from conversation content
    lower = summary.lower()
    if any(w in lower for w in ("disease", "infect", "blight", "wilt", "rot", "virus", "fungal", "bacterial")):
        obs_type = "disease_sighting"
    elif any(w in lower for w in ("treatment", "spray", "apply", "fertiliz")):
        obs_type = "treatment_applied"
    else:
        obs_type = "note"

    # Validate image path — gracefully skip if file was cleaned up
    try:
        validated_image = _validate_image_path(body.image_path)
    except HTTPException:
        validated_image = None

    try:
        result = log_observation(
            obs_type=obs_type,
            details=summary,
            image_path=validated_image,
        )
    except RuntimeError:
        raise HTTPException(503, "Knowledge Pack was unloaded during save")

    return SaveToJournalResponse(
        observation_id=result["observation_id"],
        summary=summary,
    )


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    """WebSocket endpoint for streaming field assistant responses.

    Client sends JSON:
        {
            "message": "...",
            "image_path": null,
            "conversation_history": [...],
            "conversation_summary": "...",
            "session_id": "..."
        }

    Server streams JSON events:
        {"type": "status", "step": "...", "detail": "..."}
        {"type": "node_complete", "node": "...", "tool_calls_log_entry": {...}}
        {"type": "token", "content": "..."}
        {"type": "sources", "sources": [...]}
        {"type": "answer_done"}
        {"type": "done", "final_answer": "...", "conversation_history": [...],
         "conversation_summary": "...", "tool_calls_log": [...]}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    _rate_timestamps: list[float] = []
    try:
        while True:
            data = await websocket.receive_text()

            # Rate limiting: evict timestamps outside the window, then check count
            now = time.monotonic()
            _rate_timestamps = [t for t in _rate_timestamps if now - t < _WS_RATE_LIMIT_WINDOW]
            if len(_rate_timestamps) >= _WS_RATE_LIMIT_MAX:
                await websocket.send_json({
                    "type": "error",
                    "message": "Rate limit exceeded: max 10 messages per 10 seconds",
                })
                await websocket.close(code=1008)
                return
            _rate_timestamps.append(now)

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            message = msg.get("message", "")
            if not message or len(message) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty or oversized message",
                })
                continue

            # Demo mode: replay from script.json, no LLM/ChromaDB needed
            if settings.demo_mode:
                try:
                    await replay_field_chat_ws(
                        websocket, message,
                        image_path=msg.get("image_path"),
                        msg=msg,
                    )
                except Exception as e:
                    _logger.exception("Demo replay error")
                    await websocket.send_json({"type": "error", "message": str(e)})
                continue

            pack = get_active_pack()
            if pack is None:
                await websocket.send_json({
                    "type": "error",
                    "message": "No Knowledge Pack loaded. Load a pack first.",
                })
                continue

            try:
                validated_image = _validate_image_path(msg.get("image_path"))
            except HTTPException as e:
                await websocket.send_json({"type": "error", "message": e.detail})
                continue

            try:
                async with _pipeline_lock:
                    async for event in run_field_assistant_stream(
                        message=message,
                        image_path=validated_image,
                        conversation_history=msg.get("conversation_history", [])[:50],
                        conversation_summary=msg.get("conversation_summary", ""),
                        session_id=msg.get("session_id"),
                        language=msg.get("language"),
                    ):
                        await websocket.send_json(event)
            except Exception as e:
                _logger.exception("Pipeline error")
                await websocket.send_json({
                    "type": "error",
                    "message": "Pipeline error. Check server logs.",
                })

    except WebSocketDisconnect:
        pass
