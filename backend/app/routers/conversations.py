"""Conversation history CRUD router.

Persists chat conversations to SQLite for the sidebar history UI.
Field conversations are stored per-pack in knowledge.db.
Mission conversations are stored globally in data/conversations.db.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.knowledge_pack.loader import get_active_pack
from app.knowledge_pack.schema_sqlite import ensure_conversations_tables

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ── Pydantic models ──────────────────────────────────────────

class ConversationCreate(BaseModel):
    type: Literal["field", "mission"]
    title: str = "New conversation"


class ConversationSummary(BaseModel):
    id: str
    type: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageData(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    image_path: str | None = None
    metadata: dict | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    messages: list[MessageData] = Field(default_factory=list)
    summary: str = ""


class ConversationDetail(BaseModel):
    id: str
    type: str
    title: str
    created_at: str
    updated_at: str
    messages: list[MessageData]
    summary: str


# ── DB helper ────────────────────────────────────────────────

_tables_ensured: set[str] = set()


def _get_conv_db(conv_type: str) -> sqlite3.Connection:
    """Return a writable connection to the appropriate conversations DB."""
    if conv_type == "field":
        pack = get_active_pack()
        if pack is None:
            raise HTTPException(
                status_code=503,
                detail="No Knowledge Pack loaded. Load a pack first via POST /packs/load/{pack_id}.",
            )
        db_path = pack.path / "knowledge.db"
    else:
        db_path = settings.data_path / "conversations.db"

    db_key = str(db_path)
    if db_key not in _tables_ensured:
        ensure_conversations_tables(db_path)
        _tables_ensured.add(db_key)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Endpoints ────────────────────────────────────────────────

@router.get("/", response_model=list[ConversationSummary])
async def list_conversations(type: Literal["field", "mission"] = Query(...)):
    """List conversations, sorted by most recent first."""
    conn = _get_conv_db(type)
    try:
        rows = conn.execute(
            "SELECT id, type, title, created_at, updated_at, message_count "
            "FROM conversations WHERE type = ? ORDER BY updated_at DESC LIMIT 50",
            (type,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/", response_model=ConversationDetail)
async def create_conversation(req: ConversationCreate):
    """Create a new conversation."""
    conn = _get_conv_db(req.type)
    now = datetime.now(timezone.utc).isoformat()
    conv_id = uuid.uuid4().hex[:12]

    try:
        conn.execute(
            "INSERT INTO conversations (id, type, title, created_at, updated_at, message_count, summary) "
            "VALUES (?, ?, ?, ?, ?, 0, '')",
            (conv_id, req.type, req.title, now, now),
        )
        conn.commit()
    finally:
        conn.close()

    return ConversationDetail(
        id=conv_id,
        type=req.type,
        title=req.title,
        created_at=now,
        updated_at=now,
        messages=[],
        summary="",
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    type: Literal["field", "mission"] = Query(...),
):
    """Get a conversation with all its messages."""
    conn = _get_conv_db(type)
    try:
        row = conn.execute(
            "SELECT id, type, title, created_at, updated_at, summary "
            "FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        msg_rows = conn.execute(
            "SELECT role, content, image_path, metadata "
            "FROM conversation_messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,),
        ).fetchall()

        messages = []
        for m in msg_rows:
            meta = None
            if m["metadata"]:
                try:
                    meta = json.loads(m["metadata"])
                except json.JSONDecodeError:
                    meta = None
            messages.append(MessageData(
                role=m["role"],
                content=m["content"],
                image_path=m["image_path"],
                metadata=meta,
            ))

        return ConversationDetail(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            messages=messages,
            summary=row["summary"] or "",
        )
    finally:
        conn.close()


@router.put("/{conversation_id}", response_model=ConversationDetail)
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdate,
    type: Literal["field", "mission"] = Query(...),
):
    """Update a conversation (full message replace)."""
    conn = _get_conv_db(type)
    now = datetime.now(timezone.utc).isoformat()

    try:
        # Verify conversation exists
        exists = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Delete existing messages and re-insert (full replace)
        conn.execute(
            "DELETE FROM conversation_messages WHERE conversation_id = ?",
            (conversation_id,),
        )

        for msg in req.messages:
            meta_json = json.dumps(msg.metadata) if msg.metadata else None
            conn.execute(
                "INSERT INTO conversation_messages (conversation_id, role, content, image_path, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (conversation_id, msg.role, msg.content, msg.image_path, meta_json, now),
            )

        update_fields = {
            "updated_at": now,
            "message_count": len(req.messages),
            "summary": req.summary,
        }
        if req.title is not None:
            update_fields["title"] = req.title

        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        conn.execute(
            f"UPDATE conversations SET {set_clause} WHERE id = ?",
            (*update_fields.values(), conversation_id),
        )
        conn.commit()

        # Return updated conversation
        row = conn.execute(
            "SELECT id, type, title, created_at, updated_at, summary "
            "FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()

        return ConversationDetail(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            messages=req.messages,
            summary=row["summary"] or "",
        )
    finally:
        conn.close()
