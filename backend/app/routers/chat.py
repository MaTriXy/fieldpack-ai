import json

from fastapi import APIRouter, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str
    image_path: str | None = None
    pack_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = []
    sources: list[str] = []


@router.post("/", response_model=ChatResponse)
async def chat(msg: ChatMessage):
    """Send a message to the field assistant (HTTP, non-streaming)."""
    # TODO: wire to field_assistant agent
    return ChatResponse(
        reply=f"[stub] Received: {msg.message}",
        tool_calls=[],
        sources=[],
    )


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket):
    """WebSocket endpoint for streaming field assistant responses."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # TODO: wire to field_assistant agent with streaming
            await websocket.send_json({
                "type": "token",
                "content": f"[stub] Received: {msg.get('message', '')}",
            })
            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass
