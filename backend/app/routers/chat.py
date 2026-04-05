import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.agents.field_assistant import run_field_assistant, run_field_assistant_stream
from app.config import settings
from app.knowledge_pack.loader import get_active_pack

# Serialize pipeline runs — the singleton PipelineLogger is not safe
# for concurrent pipelines sharing the same session counters.
_pipeline_lock = asyncio.Lock()

router = APIRouter(prefix="/chat", tags=["chat"])
_logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096


class ChatMessage(BaseModel):
    message: str = Field(max_length=MAX_MESSAGE_LENGTH)
    image_path: str | None = None
    conversation_history: list[dict] = Field(default_factory=list, max_length=50)
    conversation_summary: str = ""
    session_id: str | None = None


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
    """Validate image_path is within allowed directories."""
    if image_path is None:
        return None
    p = Path(image_path).resolve()
    uploads_root = settings.uploads_path.resolve()
    packs_root = settings.packs_path.resolve()
    if not (p.is_relative_to(uploads_root) or p.is_relative_to(packs_root)):
        raise HTTPException(status_code=400, detail="Invalid image path")
    if not p.is_file():
        raise HTTPException(status_code=400, detail="Image file not found")
    return str(p)


@router.post("/", response_model=ChatResponse)
async def chat(msg: ChatMessage):
    """Send a message to the field assistant (HTTP, non-streaming)."""
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
    try:
        while True:
            data = await websocket.receive_text()

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
