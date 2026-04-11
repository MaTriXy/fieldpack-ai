"""FieldPack AI Field Assistant — LangGraph State Graph.

The core agentic RAG pipeline. Wires all nodes into a StateGraph
with conditional edges, retry loops, and observation short-circuit.

Graph structure:
  classify → route → needs_search
    → [no search + observation] → log_observation → END
    → [no search + other]       → generate_answer → END
    → [needs search]            → craft_query → execute_search → rerank
        → [sufficient OR max attempts]  → generate_answer → END
        → [attempt 2]                   → expand_route → craft_query (loop)
        → [attempt 1]                   → craft_query (loop, same route)

LLM calls: classify (#1), craft_query (#2), rerank (#3), generate (#4)
           + needs_search (ambiguous cases only)
           + log_observation (observation path only)
Retry: max 3 attempts. Attempt 1 = same route new query.
       Attempt 2 = expanded route new query variants.
"""

import time
from datetime import datetime

from langgraph.graph import END, StateGraph

from app.config import settings
from app.agents.history import build_conversation_summary
from app.agents.models import IntentType
from app.agents.nodes import (
    classify_and_extract,
    craft_search_query,
    execute_searches,
    expand_route_node,
    generate_answer,
    log_observation_node,
    needs_search_node,
    rerank_results,
    route_intent,
)
from app.agents.nodes.rerank import MAX_RESULTS_FOR_RERANK
from app.agents.state import FieldAssistantState
from app.logger import Step, pipeline_logger as log


# ============================================================
# JSON serialization safety
# ============================================================

def _json_safe(obj):
    """Convert an object to a JSON-safe representation."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)


# ============================================================
# Conditional edge functions
# ============================================================

def _after_classify(state: FieldAssistantState) -> str:
    """Route after classify. Short-circuits to END if classify already set final_answer (ask-back)."""
    if state.get("final_answer"):
        return END
    return "route_intent"


def _after_needs_search(state: FieldAssistantState) -> str:
    """Route after needs_search gate.

    Three paths:
      - observation intent → log_observation_node
      - no search needed → generate_answer (use existing context)
      - search needed → craft_search_query
    """
    needs_search = state.get("needs_search", True)
    classify_result = state.get("classify_result")

    if not needs_search:
        if classify_result and classify_result.intent == IntentType.LOG_OBSERVATION:
            return "log_observation_node"
        return "generate_answer"

    return "craft_search_query"


def _after_rerank(state: FieldAssistantState) -> str:
    """Route after rerank results.

    Three paths:
      - sufficient results OR max attempts → generate_answer
      - attempt 2 → expand_route_node (broaden, then re-craft)
      - attempt 1 → craft_search_query (same route, new query)
    """
    is_sufficient = state.get("is_sufficient", False)
    attempts = state.get("retrieval_attempts", 0)

    if is_sufficient or attempts >= 3:
        return "generate_answer"

    if attempts == 2:
        return "expand_route_node"

    # attempt 1: retry with same route, new query
    return "craft_search_query"


# ============================================================
# Graph builder
# ============================================================

def build_field_assistant_graph() -> StateGraph:
    """Build the LangGraph StateGraph for the field assistant pipeline.

    Returns the compiled graph ready for invocation.
    """
    graph = StateGraph(FieldAssistantState)

    # Add all nodes
    graph.add_node("classify_and_extract", classify_and_extract)
    graph.add_node("route_intent", route_intent)
    graph.add_node("needs_search_node", needs_search_node)
    graph.add_node("log_observation_node", log_observation_node)
    graph.add_node("craft_search_query", craft_search_query)
    graph.add_node("execute_searches", execute_searches)
    graph.add_node("rerank_results", rerank_results)
    graph.add_node("expand_route_node", expand_route_node)
    graph.add_node("generate_answer", generate_answer)

    # Entry + classify → conditional (ask-back short-circuit or continue)
    graph.set_entry_point("classify_and_extract")
    graph.add_conditional_edges(
        "classify_and_extract",
        _after_classify,
        {
            END: END,
            "route_intent": "route_intent",
        },
    )
    graph.add_edge("route_intent", "needs_search_node")

    # Conditional: after needs_search gate
    graph.add_conditional_edges(
        "needs_search_node",
        _after_needs_search,
        {
            "log_observation_node": "log_observation_node",
            "generate_answer": "generate_answer",
            "craft_search_query": "craft_search_query",
        },
    )

    # Observation path → END
    graph.add_edge("log_observation_node", END)

    # Search loop
    graph.add_edge("craft_search_query", "execute_searches")
    graph.add_edge("execute_searches", "rerank_results")

    # Conditional: after rerank (retry loop)
    graph.add_conditional_edges(
        "rerank_results",
        _after_rerank,
        {
            "generate_answer": "generate_answer",
            "expand_route_node": "expand_route_node",
            "craft_search_query": "craft_search_query",
        },
    )

    # Expand route feeds back into craft_query
    graph.add_edge("expand_route_node", "craft_search_query")

    # Answer → END
    graph.add_edge("generate_answer", END)

    return graph.compile()


# Module-level compiled graph (singleton)
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_field_assistant_graph()
    return _graph


# ============================================================
# Entry points
# ============================================================

async def run_field_assistant(
    message: str,
    image_path: str | None = None,
    conversation_history: list[dict] | None = None,
    conversation_summary: str = "",
    session_id: str | None = None,
    language: str | None = None,
) -> dict:
    """Run the field assistant pipeline.

    Main entry point for the agentic RAG graph.

    Args:
        message: User's text message.
        image_path: Optional path to an uploaded plant image.
        conversation_history: Prior conversation messages.
        conversation_summary: Heuristic summary of prior conversation.
        session_id: Optional session ID for logging.

    Returns:
        Dict with: final_answer, conversation_history, conversation_summary,
        and optionally observation_stats, tool_calls_log.
    """
    log.pipeline_start(user_message=message, session_id=session_id)

    initial_state: FieldAssistantState = {
        "user_message": message,
        "image_path": image_path,
        "conversation_history": conversation_history or [],
        "conversation_summary": conversation_summary,
        "language": language,
    }

    try:
        graph = _get_graph()
        final_state = await graph.ainvoke(initial_state)

        # Build heuristic conversation summary
        summary = build_conversation_summary(
            classify_result=final_state.get("classify_result"),
            final_answer=final_state.get("final_answer", ""),
            previous_summary=conversation_summary,
        )

        log.pipeline_end(success=True)

        return {
            "final_answer": final_state.get("final_answer", ""),
            "conversation_history": final_state.get("conversation_history", []),
            "conversation_summary": summary,
            "observation_stats": final_state.get("observation_stats"),
            "tool_calls_log": log.to_tool_calls_log(),
            "classify_result": final_state.get("classify_result"),
            "ranked_results": final_state.get("ranked_results", []),
            "retrieval_attempts": final_state.get("retrieval_attempts", 0),
        }

    except Exception as e:
        log.pipeline_end(success=False, error=str(e))
        raise


_TABLE_LABELS = {
    "crops": "Crop Profile",
    "diseases": "Disease Record",
    "treatments": "Treatment Record",
    "varieties": "Variety Info",
    "climate": "Climate Data",
    "fertilization_schedule": "Fertilization Schedule",
    "planting_calendar": "Planting Calendar",
    "storage_guidelines": "Storage Guidelines",
    "soil_requirements": "Soil Requirements",
    "pests": "Pest Record",
}


def _build_source_title(metadata: dict, source_id: str) -> str:
    """Build a human-readable source title from chunk metadata."""
    disease = metadata.get("disease_name", "")
    crop = metadata.get("crop", "")
    topic = metadata.get("topic", "")

    # Disease/treatment chunks have disease_name + crop
    if disease and crop:
        topic_id = metadata.get("topic_id", "")
        if "treatment" in topic_id:
            return f"{disease} — Treatment ({crop})"
        elif "prevention" in topic_id:
            return f"{disease} — Prevention ({crop})"
        else:
            return f"{disease} — Symptoms ({crop})"

    # Farming practices have topic + crop
    if topic and crop:
        return f"{topic.replace('_', ' ').title()} — {crop.title()}"

    # Regional context has topic only
    if topic:
        return topic.replace("_", " ").title()

    # FTS/structured results use "table:id" format
    if ":" in source_id:
        table, _, row_id = source_id.partition(":")
        label = _TABLE_LABELS.get(table, table.replace("_", " ").title())
        return f"{label} #{row_id}"

    # Fallback: clean up the doc ID
    return source_id.replace("_", " ").rsplit(" child", 1)[0].rsplit(" parent", 1)[0].title() or "Unknown Source"


async def run_field_assistant_stream(
    message: str,
    image_path: str | None = None,
    conversation_history: list[dict] | None = None,
    conversation_summary: str = "",
    session_id: str | None = None,
    language: str | None = None,
):
    """Stream the field assistant pipeline via astream_events.

    Yields event dicts for the WebSocket handler to forward to the client.

    Event types:
        {"type": "status", "step": "...", "detail": "..."}
        {"type": "token", "content": "..."}  (from generate_answer streaming)
        {"type": "answer_done"}
        {"type": "sources", "sources": [...]}
        {"type": "done", "tool_calls_log": [...]}
        {"type": "error", "message": "..."}
    """
    log.pipeline_start(user_message=message, session_id=session_id)

    initial_state: FieldAssistantState = {
        "user_message": message,
        "image_path": image_path,
        "conversation_history": conversation_history or [],
        "conversation_summary": conversation_summary,
        "language": language,
    }

    _NODE_STATUS_MAP = {
        "classify_and_extract": ("classifying", "Analyzing your question..."),
        "route_intent": ("routing", "Planning search strategy..."),
        "needs_search_node": ("evaluating", "Deciding if search is needed..."),
        "log_observation_node": ("saving", "Saving your observation..."),
        "craft_search_query": ("crafting", "Preparing search queries..."),
        "execute_searches": ("searching", "Searching knowledge base..."),
        "rerank_results": ("reranking", "Evaluating result quality..."),
        "expand_route_node": ("expanding", "Broadening search strategy..."),
        "generate_answer": ("generating", "Composing answer..."),
    }

    try:
        graph = _get_graph()
        final_state = {}
        node_timings: dict[str, float] = {}
        llm_call_count = 0
        _LLM_NODES = {
            "classify_and_extract", "craft_search_query",
            "rerank_results", "generate_answer", "needs_search_node",
        }
        pipeline_start = time.perf_counter()

        in_generate = False

        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            # Node start → status event + record start time
            if kind == "on_chain_start" and name in _NODE_STATUS_MAP:
                in_generate = (name == "generate_answer")
                node_timings[name] = time.perf_counter()
                step, detail = _NODE_STATUS_MAP[name]
                tcl = log.to_tool_calls_log()
                yield {
                    "type": "status",
                    "step": step,
                    "detail": detail,
                    "tool_calls_log_entry": tcl[-1:] if tcl else None,
                }

            # Node end → emit tool_calls_log + node_stats with latency
            if kind == "on_chain_end" and name in _NODE_STATUS_MAP:
                if name == "generate_answer":
                    in_generate = False
                latency_ms = None
                if name in node_timings:
                    latency_ms = round((time.perf_counter() - node_timings[name]) * 1000)
                    if name in _LLM_NODES:
                        llm_call_count += 1

                entries = log.to_tool_calls_log()
                if entries:
                    yield {
                        "type": "node_complete",
                        "node": name,
                        "tool_calls_log_entry": entries[-1],
                    }

                yield {
                    "type": "node_stats",
                    "node": name,
                    "latency_ms": latency_ms,
                    "model": settings.ollama_model,
                }

            # Accumulate all node outputs into final_state
            if kind == "on_chain_end" and name in _NODE_STATUS_MAP:
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict):
                    final_state.update(output)

                # After needs_search decision, tell frontend which path we're on
                if name == "needs_search_node":
                    yield {
                        "type": "pipeline_mode",
                        "mode": "rag" if final_state.get("needs_search", True) else "quick",
                    }

            # Stream LLM tokens from generate_answer only
            if kind == "on_chat_model_stream" and in_generate:
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {"type": "token", "content": chunk.content}

        # Build summary from final state
        if final_state and (final_state.get("final_answer") is not None or final_state.get("observation_stats") is not None):
            summary = build_conversation_summary(
                classify_result=final_state.get("classify_result"),
                final_answer=final_state.get("final_answer", ""),
                previous_summary=conversation_summary,
            )

            # Sources from ranked results — cap at MAX_RESULTS_FOR_RERANK
            ranked = final_state.get("ranked_results", [])[:MAX_RESULTS_FOR_RERANK]
            sources = []
            for r in ranked:
                if not hasattr(r, "relevance_score"):
                    continue
                meta = getattr(r, "metadata", {}) or {}
                title = _build_source_title(meta, r.source)
                sources.append({
                    "title": title,
                    "score": round(r.relevance_score, 3),
                    "content": r.parent_content or r.content or "",
                })

            if sources:
                yield {"type": "sources", "sources": sources}

            if final_state.get("final_answer"):
                yield {"type": "answer_done"}

            log.pipeline_end(success=True)

            total_latency_ms = round((time.perf_counter() - pipeline_start) * 1000)

            yield _json_safe({
                "type": "done",
                "final_answer": final_state.get("final_answer", ""),
                "conversation_history": final_state.get("conversation_history", []),
                "conversation_summary": summary,
                "observation_stats": final_state.get("observation_stats"),
                "tool_calls_log": log.to_tool_calls_log(),
                "total_latency_ms": total_latency_ms,
                "llm_calls": llm_call_count,
                "model": settings.ollama_model,
                "image_description": final_state.get("image_description"),
            })
        else:
            log.pipeline_end(success=False, error="No final state produced")
            yield {"type": "error", "message": "Pipeline completed without producing a result"}

    except Exception as e:
        log.pipeline_end(success=False, error=str(e))
        log.log_step(Step.GENERATE, "streaming_error", level="ERROR",
                     details={"error": str(e)})
        yield {"type": "error", "message": "Pipeline error. Please try again."}
