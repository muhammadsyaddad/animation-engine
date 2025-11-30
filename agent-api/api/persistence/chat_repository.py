"""
Chat Repository
================

Low-level CRUD/data-access utilities for chat session & message persistence.

Schema (see db/schema_local.sql):
---------------------------------
    create table public.chat_sessions (
      id uuid primary key default gen_random_uuid(),
      user_id uuid references public.users(id) on delete cascade,
      name text,
      created_at timestamptz default now(),
      updated_at timestamptz default now()
    );

    create table public.chat_messages (
      id uuid primary key default gen_random_uuid(),
      session_id uuid references public.chat_sessions(id) on delete cascade,
      user_id uuid references public.users(id) on delete set null,
      role text not null check (role in ('user','agent','system','tool')),
      content text not null,
      extra_json jsonb,
      created_at timestamptz default now()
    );

Design Goals:
-------------
- Keep this repository pure (no FastAPI dependencies) so it can be reused by
  background jobs or tests.
- Favor explicit SQL (sqlalchemy.text) for clarity & easy migration (e.g. Supabase).
- Dataclasses for return objects; avoid ORM models for minimal coupling.
- Functions auto-commit by default (configurable via commit flag).
- Graceful handling of missing rows (return None rather than raising unless
  function semantics require exception).

Migration Notes (Supabase):
---------------------------
- Replace FK to public.users with auth.users(id).
- Optionally enable Row Level Security and policies:
    alter table public.chat_sessions enable row level security;
    create policy "own sessions" on public.chat_sessions
      for all using (auth.uid() = user_id);
    ... similarly for chat_messages.
- Replace manual updated_at trigger if using Supabase managed solutions.

"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Iterable, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class ChatSession:
    id: str
    user_id: str
    name: Optional[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class ChatMessage:
    id: str
    session_id: str
    role: str
    content: str
    user_id: Optional[str] = None
    extra_json: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


# =============================================================================
# Exceptions
# =============================================================================


class ChatRepositoryError(Exception):
    """Generic repository error."""


class ChatSessionNotFound(ChatRepositoryError):
    """Raised when a chat session is not found."""


class ChatMessageNotFound(ChatRepositoryError):
    """Raised when a chat message is not found."""


# =============================================================================
# Helpers & Mappers
# =============================================================================


_VALID_ROLES = {"user", "agent", "system", "tool"}


def _row_to_session(row: Any) -> ChatSession:
    return ChatSession(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        name=row.get("name"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _row_to_message(row: Any) -> ChatMessage:
    return ChatMessage(
        id=str(row["id"]),
        session_id=str(row["session_id"]),
        role=row["role"],
        content=row["content"],
        user_id=(str(row["user_id"]) if row.get("user_id") else None),
        extra_json=row.get("extra_json"),
        created_at=row.get("created_at"),
    )


def _validate_role(role: str) -> None:
    if role not in _VALID_ROLES:
        raise ChatRepositoryError(f"Invalid role '{role}'. Must be one of {_VALID_ROLES}.")


# =============================================================================
# Chat Session CRUD
# =============================================================================


def create_chat_session(
    session: Session,
    user_id: str,
    name: Optional[str] = None,
    commit: bool = True,
) -> ChatSession:
    sql = text(
        """
        insert into public.chat_sessions (user_id, name)
        values (:user_id, :name)
        returning id, user_id, name, created_at, updated_at
        """
    )
    try:
        row = session.execute(sql, {"user_id": user_id, "name": name}).mappings().first()
        if commit:
            session.commit()
    except Exception as e:
        session.rollback()
        raise ChatRepositoryError(f"Failed to create chat session: {e}") from e
    if not row:
        raise ChatRepositoryError("Insert returned no row.")
    return _row_to_session(row)


def get_chat_session(session: Session, session_id: str) -> Optional[ChatSession]:
    sql = text(
        """
        select id, user_id, name, created_at, updated_at
        from public.chat_sessions
        where id = :id
        limit 1
        """
    )
    row = session.execute(sql, {"id": session_id}).mappings().first()
    if not row:
        return None
    return _row_to_session(row)


def list_chat_sessions(
    session: Session,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[ChatSession]:
    if user_id is None:
        sql = text(
            """
            select id, user_id, name, created_at, updated_at
            from public.chat_sessions
            order by updated_at desc
            limit :limit offset :offset
            """
        )
        params = {"limit": limit, "offset": offset}
    else:
        sql = text(
            """
            select id, user_id, name, created_at, updated_at
            from public.chat_sessions
            where user_id = :uid
            order by updated_at desc
            limit :limit offset :offset
            """
        )
        params = {"uid": user_id, "limit": limit, "offset": offset}
    rows = session.execute(sql, params).mappings().all()
    return [_row_to_session(r) for r in rows]


def rename_chat_session(
    session: Session,
    session_id: str,
    new_name: Optional[str],
    commit: bool = True,
) -> Optional[ChatSession]:
    sql = text(
        """
        update public.chat_sessions
        set name = :name
        where id = :id
        returning id, user_id, name, created_at, updated_at
        """
    )
    try:
        row = session.execute(sql, {"id": session_id, "name": new_name}).mappings().first()
        if commit:
            session.commit()
    except Exception as e:
        session.rollback()
        raise ChatRepositoryError(f"Failed to rename chat session: {e}") from e
    if not row:
        return None
    return _row_to_session(row)


def delete_chat_session(
    session: Session,
    session_id: str,
    commit: bool = True,
) -> bool:
    sql = text("delete from public.chat_sessions where id = :id")
    try:
        res = session.execute(sql, {"id": session_id})
        deleted = (getattr(res, "rowcount", 0) or 0) > 0
        if commit:
            session.commit()
        return deleted
    except Exception as e:
        session.rollback()
        raise ChatRepositoryError(f"Failed to delete chat session: {e}") from e


# =============================================================================
# Chat Message CRUD
# =============================================================================


def create_chat_message(
    session: Session,
    session_id: str,
    role: str,
    content: str,
    user_id: Optional[str] = None,
    extra_json: Optional[Dict[str, Any]] = None,
    commit: bool = True,
) -> ChatMessage:
    _validate_role(role)
    # Note: extra_json is passed as a JSON string (if dict) and cast to jsonb explicitly.
    # Use CAST(:extra_json AS jsonb) to avoid mixed param styles causing a colon bind to leak.
    sql = text(
        """
        insert into public.chat_messages (session_id, user_id, role, content, extra_json)
        values (:session_id, :user_id, :role, :content, CAST(:extra_json AS jsonb))
        returning id, session_id, user_id, role, content, extra_json, created_at
        """
    )
    try:
        row = session.execute(
            sql,
            {
                "session_id": session_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "extra_json": (
                    json.dumps(extra_json)
                    if isinstance(extra_json, dict)
                    else (extra_json if extra_json is not None else None)
                ),
            },
        ).mappings().first()
        if commit:
            session.commit()
    except Exception as e:
        session.rollback()
        raise ChatRepositoryError(f"Failed to create chat message: {e}") from e
    if not row:
        raise ChatRepositoryError("Insert message returned no row.")
    return _row_to_message(row)


def get_chat_message(session: Session, message_id: str) -> Optional[ChatMessage]:
    sql = text(
        """
        select id, session_id, user_id, role, content, extra_json, created_at
        from public.chat_messages
        where id = :id
        limit 1
        """
    )
    row = session.execute(sql, {"id": message_id}).mappings().first()
    if not row:
        return None
    return _row_to_message(row)


def list_chat_messages(
    session: Session,
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    ascending: bool = True,
) -> List[ChatMessage]:
    order = "asc" if ascending else "desc"
    sql = text(
        f"""
        select id, session_id, user_id, role, content, extra_json, created_at
        from public.chat_messages
        where session_id = :sid
        order by created_at {order}
        limit :limit offset :offset
        """
    )
    rows = session.execute(
        sql, {"sid": session_id, "limit": limit, "offset": offset}
    ).mappings().all()
    return [_row_to_message(r) for r in rows]


def delete_chat_message(
    session: Session,
    message_id: str,
    commit: bool = True,
) -> bool:
    sql = text("delete from public.chat_messages where id = :id")
    try:
        res = session.execute(sql, {"id": message_id})
        deleted = (getattr(res, "rowcount", 0) or 0) > 0
        if commit:
            session.commit()
        return deleted
    except Exception as e:
        session.rollback()
        raise ChatRepositoryError(f"Failed to delete chat message: {e}") from e


# =============================================================================
# Bulk / Utility
# =============================================================================


def bulk_get_sessions(session: Session, session_ids: Iterable[str]) -> Dict[str, ChatSession]:
    ids = list({s for s in session_ids})
    if not ids:
        return {}
    sql = text(
        """
        select id, user_id, name, created_at, updated_at
        from public.chat_sessions
        where id = any(:ids)
        """
    )
    rows = session.execute(sql, {"ids": ids}).mappings().all()
    return {str(r["id"]): _row_to_session(r) for r in rows}


def bulk_get_messages(session: Session, message_ids: Iterable[str]) -> Dict[str, ChatMessage]:
    ids = list({m for m in message_ids})
    if not ids:
        return {}
    sql = text(
        """
        select id, session_id, user_id, role, content, extra_json, created_at
        from public.chat_messages
        where id = any(:ids)
        """
    )
    rows = session.execute(sql, {"ids": ids}).mappings().all()
    return {str(r["id"]): _row_to_message(r) for r in rows}
