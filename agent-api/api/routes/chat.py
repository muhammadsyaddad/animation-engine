"""
Chat Routes
===========

FastAPI router exposing CRUD endpoints for chat sessions and messages.

Tables (defined in db/schema_local.sql):
---------------------------------------
- public.chat_sessions
- public.chat_messages

Auth:
-----
- Creating sessions & messages requires authentication (Bearer token).
- Reading can be public (but user_only filter requires auth).
- Ownership enforced for modifying / deleting sessions or deleting messages.

Endpoints:
----------
POST   /v1/chat/sessions
GET    /v1/chat/sessions
GET    /v1/chat/sessions/{session_id}
PATCH  /v1/chat/sessions/{session_id}
DELETE /v1/chat/sessions/{session_id}

POST   /v1/chat/sessions/{session_id}/messages
GET    /v1/chat/sessions/{session_id}/messages
DELETE /v1/chat/messages/{message_id}

Future (optional):
------------------
- SSE / WebSocket streaming for real-time message delivery
- Search/filter endpoints (by keyword, date range, role)
- RLS policies on Supabase migration
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from db.session import get_db
from api.routes.auth import (
    get_current_user,
    get_current_user_optional,
)
from api.persistence.chat_repository import (
    create_chat_session,
    list_chat_sessions,
    get_chat_session,
    rename_chat_session,
    delete_chat_session,
    create_chat_message,
    list_chat_messages,
    delete_chat_message,
    get_chat_message,
    ChatSession,
    ChatMessage,
)

# ------------------------------------------------------------------------------
# Router
# ------------------------------------------------------------------------------
chat_router = APIRouter(prefix="/chat", tags=["chat"])


# ------------------------------------------------------------------------------
# Pydantic Schemas
# ------------------------------------------------------------------------------

class ChatSessionOut(BaseModel):
    id: str
    user_id: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    user_id: Optional[str] = None
    extra_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class CreateSessionRequest(BaseModel):
    name: Optional[str] = Field(
        None, description="Optional human-friendly name for the new session."
    )


class CreateMessageRequest(BaseModel):
    role: str = Field(..., description="Role: user | agent | system | tool")
    content: str = Field(..., description="Message content (text).")
    extra_json: Optional[Dict[str, Any]] = Field(
        None, description="Optional structured metadata (tool calls, reasoning, etc)."
    )


class SessionListResponse(BaseModel):
    sessions: List[ChatSessionOut]


class MessageListResponse(BaseModel):
    messages: List[ChatMessageOut]


class CreateSessionResponse(BaseModel):
    session: ChatSessionOut


class CreateMessageResponse(BaseModel):
    message: ChatMessageOut


class RenameSessionRequest(BaseModel):
    name: Optional[str] = Field(None, description="New name (or null to clear).")


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def to_session_out(s: ChatSession) -> ChatSessionOut:
    return ChatSessionOut(
        id=s.id,
        user_id=s.user_id,
        name=s.name,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def to_message_out(m: ChatMessage) -> ChatMessageOut:
    return ChatMessageOut(
        id=m.id,
        session_id=m.session_id,
        role=m.role,
        content=m.content,
        user_id=m.user_id,
        extra_json=m.extra_json,
        created_at=m.created_at,
    )


# ------------------------------------------------------------------------------
# Session Endpoints
# ------------------------------------------------------------------------------

@chat_router.post(
    "/sessions",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    body: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create a new chat session for the authenticated user.
    """
    session_row = create_chat_session(
        db,
        user_id=current_user.id,
        name=body.name,
        commit=True,
    )
    return CreateSessionResponse(session=to_session_out(session_row))


@chat_router.get(
    "/sessions",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
)
def list_sessions(
    user_only: bool = Query(
        default=True,
        description="If true, returns only sessions owned by authenticated user. If false, returns all sessions.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    List chat sessions. By default (user_only=True) requires auth to return user's sessions.
    If user_only=False and no auth provided, returns all sessions (local dev scenario).
    """
    target_user_id: Optional[str] = None
    if user_only:
        if not current_user:
            # Enforce auth if user_only requested
            return SessionListResponse(sessions=[])
        target_user_id = current_user.id

    rows = list_chat_sessions(
        db,
        user_id=target_user_id,
        limit=limit,
        offset=offset,
    )
    return SessionListResponse(sessions=[to_session_out(r) for r in rows])


@chat_router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionOut,
    status_code=status.HTTP_200_OK,
)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    Fetch a single chat session. If session has a user_id, enforce ownership.
    """
    row = get_chat_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.user_id and current_user and current_user.id != row.user_id:
        raise HTTPException(status_code=403, detail="Not owner of session")
    if row.user_id and not current_user:
        raise HTTPException(status_code=403, detail="Not owner of session")
    return to_session_out(row)


@chat_router.patch(
    "/sessions/{session_id}",
    response_model=ChatSessionOut,
    status_code=status.HTTP_200_OK,
)
def rename_session(
    session_id: str,
    body: RenameSessionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Rename a chat session (owned by current user).
    """
    row = get_chat_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not owner of session")

    updated = rename_chat_session(db, session_id, new_name=body.name, commit=True)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to rename session")
    return to_session_out(updated)


@chat_router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete a chat session (and its messages).
    """
    row = get_chat_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not owner of session")

    deleted = delete_chat_session(db, session_id, commit=True)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete session")
    return {"status": "deleted", "session_id": session_id}


# ------------------------------------------------------------------------------
# Message Endpoints
# ------------------------------------------------------------------------------

@chat_router.post(
    "/sessions/{session_id}/messages",
    response_model=CreateMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    session_id: str,
    body: CreateMessageRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Append a message to a session. Enforces ownership for user messages.
    role must be one of: user | agent | system | tool
    """
    sess = get_chat_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not owner of session")

    msg = create_chat_message(
        db,
        session_id=session_id,
        role=body.role,
        content=body.content,
        user_id=current_user.id if body.role == "user" else None,
        extra_json=body.extra_json,
        commit=True,
    )
    return CreateMessageResponse(message=to_message_out(msg))


@chat_router.get(
    "/sessions/{session_id}/messages",
    response_model=MessageListResponse,
    status_code=status.HTTP_200_OK,
)
def list_messages(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ascending: bool = Query(
        default=True, description="True for chronological (oldest first); false for newest first."
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    """
    List messages in a session. Enforces ownership if session has user_id recorded.
    """
    sess = get_chat_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.user_id:
        if not current_user or current_user.id != sess.user_id:
            raise HTTPException(status_code=403, detail="Not owner of session")

    rows = list_chat_messages(
        db,
        session_id=session_id,
        limit=limit,
        offset=offset,
        ascending=ascending,
    )
    return MessageListResponse(messages=[to_message_out(r) for r in rows])


@chat_router.delete(
    "/messages/{message_id}",
    status_code=status.HTTP_200_OK,
)
def delete_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Delete a single message. Ownership enforced by checking its parent session.
    """
    msg = get_chat_message(db, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    sess = get_chat_session(db, msg.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Parent session not found")
    if sess.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not owner of session")

    deleted = delete_chat_message(db, message_id, commit=True)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete message")
    return {"status": "deleted", "message_id": message_id}


# For compatibility with import style: from api.routes.chat import router
router = chat_router
