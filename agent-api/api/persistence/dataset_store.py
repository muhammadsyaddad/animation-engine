from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session
from db.session import SessionLocal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DatasetRow:
    dataset_id: str
    user_id: Optional[str]
    filename: str
    storage_path: Optional[str]
    size_bytes: Optional[int]
    checksum: Optional[str]
    mime_type: Optional[str] = "text/csv"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _new_session(provided: Optional[Session]) -> Session:
    """Use existing session if given, otherwise create a new one."""
    return provided or SessionLocal()

def _row_to_dataset(row) -> DatasetRow:
    """Convert raw SQLAlchemy row mapping to DatasetRow dataclass."""
    return DatasetRow(
        dataset_id=row["id"],
        user_id=row.get("user_id"),
        filename=row["filename"],
        storage_path=row.get("storage_path"),
        size_bytes=row.get("size_bytes"),
        checksum=row.get("checksum"),
        mime_type=row.get("mime_type"),
    )

# ---------------------------------------------------------------------------
# Persistence functions
# ---------------------------------------------------------------------------

def persist_dataset(meta, user_id: Optional[str] = None, db: Optional[Session] = None) -> Optional[DatasetRow]:
    """
    Insert a new dataset record.
    Idempotent: if the dataset already exists, does nothing.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        sql = text("""
            insert into public.datasets (id, user_id, filename, storage_path, size_bytes, mime_type, checksum)
            values (:id, :user_id, :filename, :storage_path, :size_bytes, 'text/csv', :checksum)
            on conflict (id) do nothing
            returning id, user_id, filename, storage_path, size_bytes, mime_type, checksum
        """)
        row = session.execute(sql, {
            "id": meta.dataset_id,
            "user_id": user_id,
            "filename": (meta.unified_path and __import__('os').path.basename(meta.unified_path)) or meta.dataset_id + ".csv",
            "storage_path": meta.unified_rel_url,
            "size_bytes": meta.size_bytes,
            "checksum": meta.sha256
        }).mappings().first()

        session.commit()
        if row:
            return _row_to_dataset(row)
        return None
    except Exception as e:
        session.rollback()
        logger.warning("persist_dataset failed id=%s error=%s", meta.dataset_id, e)
        return None
    finally:
        if auto_close:
            session.close()

def delete_dataset_row(dataset_id: str, db: Optional[Session] = None):
    """Delete a dataset record by ID."""
    session = _new_session(db)
    auto_close = db is None
    try:
        session.execute(text("delete from public.datasets where id = :id"), {"id": dataset_id})
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning("delete_dataset_row failed id=%s error=%s", dataset_id, e)
    finally:
        if auto_close:
            session.close()

def list_dataset_rows(user_id: Optional[str] = None, limit: int = 50, offset: int = 0, db: Optional[Session] = None) -> List[DatasetRow]:
    """
    List datasets, optionally filtered by user_id.
    Ordered by creation time (descending).
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        if user_id:
            sql = text("""
                select id, user_id, filename, storage_path, size_bytes, mime_type, checksum
                from public.datasets
                where user_id = :user_id
                order by created_at desc
                limit :limit offset :offset
            """)
            rows = session.execute(sql, {"user_id": user_id, "limit": limit, "offset": offset}).mappings().all()
        else:
            sql = text("""
                select id, user_id, filename, storage_path, size_bytes, mime_type, checksum
                from public.datasets
                order by created_at desc
                limit :limit offset :offset
            """)
            rows = session.execute(sql, {"limit": limit, "offset": offset}).mappings().all()

        return [_row_to_dataset(r) for r in rows]
    except Exception as e:
        logger.warning("list_dataset_rows failed user_id=%s error=%s", user_id, e)
        return []
    finally:
        if auto_close:
            session.close()

# ---------------------------------------------------------------------------
# Lookup helpers (checksum / id)
# ---------------------------------------------------------------------------

def get_dataset_by_checksum(checksum: str, db: Optional[Session] = None) -> Optional[DatasetRow]:
    """
    Fetch a dataset row by checksum.
    Returns None if not found.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        sql = text("""
            select id, user_id, filename, storage_path, size_bytes, mime_type, checksum
            from public.datasets
            where checksum = :checksum
            limit 1
        """)
        row = session.execute(sql, {"checksum": checksum}).mappings().first()
        if row:
            return _row_to_dataset(row)
        return None
    except Exception as e:
        logger.warning("get_dataset_by_checksum failed checksum=%s error=%s", checksum, e)
        return None
    finally:
        if auto_close:
            session.close()

def dataset_exists_by_checksum(checksum: str, db: Optional[Session] = None) -> bool:
    """
    Returns True if a dataset with the given checksum exists.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        sql = text("select 1 from public.datasets where checksum = :checksum limit 1")
        row = session.execute(sql, {"checksum": checksum}).first()
        return row is not None
    except Exception as e:
        logger.warning("dataset_exists_by_checksum failed checksum=%s error=%s", checksum, e)
        return False
    finally:
        if auto_close:
            session.close()

def get_dataset_by_id(dataset_id: str, db: Optional[Session] = None) -> Optional[DatasetRow]:
    """
    Fetch a dataset row by id.
    """
    session = _new_session(db)
    auto_close = db is None
    try:
        sql = text("""
            select id, user_id, filename, storage_path, size_bytes, mime_type, checksum
            from public.datasets
            where id = :id
            limit 1
        """)
        row = session.execute(sql, {"id": dataset_id}).mappings().first()
        if row:
            return _row_to_dataset(row)
        return None
    except Exception as e:
        logger.warning("get_dataset_by_id failed id=%s error=%s", dataset_id, e)
        return None
    finally:
        if auto_close:
            session.close()
