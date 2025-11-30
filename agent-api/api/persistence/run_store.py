"""
Persistence helpers for agent run lifecycle and produced artifacts.

This module complements the in-memory `run_registry` by writing records
to the Postgres tables defined in `db/schema_local.sql`:
  - public.agent_runs
  - public.artifacts

Goals:
- Lightweight, explicit SQL (using SQLAlchemy text) to avoid premature ORM modeling.
- Idempotent inserts (caller guarantees uniqueness of run_id).
- Resilient error handling (log + swallow optional failures without crashing streaming).

Typical usage pattern (in endpoints / pipeline code):
------------------------------------------------------------------
from api.persistence.run_store import (
    persist_run_created,
    persist_run_state,
    persist_run_completed,
    persist_run_failed,
    persist_artifact,
)

# On run creation:
persist_run_created(run_id, user_id, session_id, agent_id="animation_agent",
                    state="STARTING", message=initial_message,
                    metadata={"aspect_ratio": aspect_ratio})

# On state transitions:
persist_run_state(run_id, "PREVIEWING", message="Generating preview...")

# On errors:
persist_run_failed(run_id, error_message)

# On completion:
persist_run_completed(run_id, message="Render completed.")

# When video/artifact produced:
persist_artifact(run_id, kind="video", storage_path="/static/videos/xyz.mp4",
                 width=1920, height=1080, duration_ms=12000)
------------------------------------------------------------------

NOTE:
- `state` uses the textual enum name from in-memory RunState (e.g. STARTING, PREVIEWING).
- Timestamps handled server-side by default (created_at / updated_at triggers or explicit updates).
- All functions open a short-lived session (recommended for streaming generators).
  Alternatively, you can pass an existing session object.

Migration Considerations (Supabase):
- Foreign key user_id will be updated to reference `auth.users.id`.
- RLS policies will be added; ensure queries include user_id filters when listing runs.
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass
from typing import Optional, Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import SessionLocal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes for typed return values
# ---------------------------------------------------------------------------

@dataclass
class RunRow:
    run_id: str
    user_id: Optional[str]
    session_id: Optional[str]
    agent_id: str
    state: str
    message: Optional[str]
    metadata: Dict[str, Any]
    created_at: Optional[str]
    updated_at: Optional[str]


@dataclass
class ArtifactRow:
    id: str
    run_id: str
    kind: str
    storage_path: str
    width: Optional[int]
    height: Optional[int]
    duration_ms: Optional[int]
    created_at: Optional[str]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _new_session(provided: Optional[Session]) -> Session:
    return provided or SessionLocal()


def _row_to_run(row) -> RunRow:
    return RunRow(
        run_id=row["run_id"],
        user_id=row.get("user_id"),
        session_id=row.get("session_id"),
        agent_id=row["agent_id"],
        state=row["state"],
        message=row.get("message"),
        metadata=row.get("metadata") or {},
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _row_to_artifact(row) -> ArtifactRow:
    return ArtifactRow(
        id=row["id"],
        run_id=row["run_id"],
        kind=row["kind"],
        storage_path=row["storage_path"],
        width=row.get("width"),
        height=row.get("height"),
        duration_ms=row.get("duration_ms"),
        created_at=row.get("created_at"),
    )


# ---------------------------------------------------------------------------
# Persistence Functions
# ---------------------------------------------------------------------------

def persist_run_created(
    run_id: str,
    user_id: Optional[str],
    session_id: Optional[str],
    agent_id: str,
    state: str,
    message: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> Optional[RunRow]:
    """
    Insert a new agent run record. Fails gracefully if duplicate exists.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        # Basic guard: convert non-UUID user_id values to None (NULL in DB)
        if user_id is not None:
            import re
            if not re.fullmatch(r"[0-9a-fA-F-]{36}", user_id):
                logger.warning("Non-UUID user_id received (%s); persisting as NULL", user_id)
                user_id = None
        sql = text(
            """
            insert into public.agent_runs (run_id, user_id, session_id, agent_id, state, message, metadata)
            values (:run_id, :user_id, :session_id, :agent_id, :state, :message, (:metadata)::jsonb)
            on conflict (run_id) do nothing
            returning run_id, user_id, session_id, agent_id, state, message, metadata, created_at, updated_at
            """
        )
        row = session.execute(
            sql,
            {
                "run_id": run_id,
                "user_id": user_id,
                "session_id": session_id,
                "agent_id": agent_id,
                "state": state,
                "message": message,
                "metadata": json.dumps(metadata or {}),
            },
        ).mappings().first()
        session.commit()
        if row:
            return _row_to_run(row)
        return None
    except Exception as e:
        session.rollback()
        logger.warning("persist_run_created failed run_id=%s error=%s", run_id, e)
        return None
    finally:
        if auto_close:
            session.close()


def persist_run_state(
    run_id: str,
    state: str,
    message: Optional[str] = None,
    db: Optional[Session] = None,
) -> bool:
    """
    Update the state (and optional message) of an existing run.
    Returns True if a row was updated.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        sql = text(
            """
            update public.agent_runs
            set state = :state,
                message = coalesce(:message, message),
                updated_at = now()
            where run_id = :run_id
            """
        )
        res = session.execute(
            sql,
            {"state": state, "message": message, "run_id": run_id},
        )
        session.commit()
        return res.rowcount > 0
    except Exception as e:
        session.rollback()
        logger.warning("persist_run_state failed run_id=%s error=%s", run_id, e)
        return False
    finally:
        if auto_close:
            session.close()


def persist_run_failed(
    run_id: str,
    error_message: str,
    db: Optional[Session] = None,
) -> bool:
    """
    Mark run as ERROR and update message.
    """
    return persist_run_state(run_id, "ERROR", message=error_message, db=db)


def persist_run_completed(
    run_id: str,
    message: Optional[str] = None,
    db: Optional[Session] = None,
) -> bool:
    """
    Mark run as COMPLETED.
    """
    return persist_run_state(run_id, "COMPLETED", message=message, db=db)


def persist_artifact(
    run_id: str,
    kind: str,
    storage_path: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    duration_ms: Optional[int] = None,
    db: Optional[Session] = None,
) -> Optional[ArtifactRow]:
    """
    Insert a produced artifact for a run.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        sql = text(
            """
            insert into public.artifacts (run_id, kind, storage_path, width, height, duration_ms)
            values (:run_id, :kind, :storage_path, :width, :height, :duration_ms)
            returning id, run_id, kind, storage_path, width, height, duration_ms, created_at
            """
        )
        row = session.execute(
            sql,
            {
                "run_id": run_id,
                "kind": kind,
                "storage_path": storage_path,
                "width": width,
                "height": height,
                "duration_ms": duration_ms,
            },
        ).mappings().first()
        session.commit()
        if row:
            return _row_to_artifact(row)
        return None
    except Exception as e:
        session.rollback()
        logger.warning(
            "persist_artifact failed run_id=%s kind=%s path=%s error=%s",
            run_id,
            kind,
            storage_path,
            e,
        )
        return None
    finally:
        if auto_close:
            session.close()


def get_run_row(run_id: str, db: Optional[Session] = None) -> Optional[RunRow]:
    """
    Fetch a persisted run row.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        sql = text(
            """
            select run_id, user_id, session_id, agent_id, state, message, metadata, created_at, updated_at
            from public.agent_runs
            where run_id = :run_id
            limit 1
            """
        )
        row = session.execute(sql, {"run_id": run_id}).mappings().first()
        if row:
            return _row_to_run(row)
        return None
    except Exception as e:
        logger.warning("get_run_row failed run_id=%s error=%s", run_id, e)
        return None
    finally:
        if auto_close:
            session.close()


def list_runs_rows(
    limit: int = 50,
    offset: int = 0,
    db: Optional[Session] = None,
) -> List[RunRow]:
    """
    List run rows ordered by created_at descending.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        sql = text(
            """
            select run_id, user_id, session_id, agent_id, state, message, metadata, created_at, updated_at
            from public.agent_runs
            order by created_at desc
            limit :limit offset :offset
            """
        )
        rows = session.execute(
            sql, {"limit": limit, "offset": offset}
        ).mappings().all()
        return [_row_to_run(r) for r in rows]
    except Exception as e:
        logger.warning("list_runs_rows failed error=%s", e)
        return []
    finally:
        if auto_close:
            session.close()
