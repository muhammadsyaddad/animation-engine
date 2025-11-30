"""
Repository layer for local authentication & profile tables.

This module provides low-level database access functions for:
- users
- profiles

It is intentionally decoupled from FastAPI dependencies so it can be
used in services, background jobs, or tests.

IMPORTANT (Local Dev Only):
In production (Supabase), the `public.users` table will be replaced by
`auth.users`. The profile & related data tables should then reference
`auth.users.id` instead. These functions are designed so that migration
will be straightforward (replace create_user / password-related logic
with Supabase Auth integration, keep profile functions).

All functions expect an active SQLAlchemy Session object. By default
they auto-commit on success (configurable via the `commit` flag).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Any, Dict, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.auth.security import hash_password, verify_password


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None


@dataclass
class Profile:
    user_id: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    created_at: Optional[str] = None


# =============================================================================
# Exceptions
# =============================================================================


class AuthRepositoryError(Exception):
    """Generic repository error."""


class UserNotFound(AuthRepositoryError):
    """Raised when a user is not found."""


class EmailAlreadyExists(AuthRepositoryError):
    """Raised on unique email violations."""


# =============================================================================
# Row Mapping Helpers
# =============================================================================


def _row_to_user(row: Any) -> User:
    return User(
        id=str(row["id"]),
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=row.get("created_at"),
        last_login_at=row.get("last_login_at"),
    )


def _row_to_profile(row: Any) -> Profile:
    return Profile(
        user_id=str(row["user_id"]),
        display_name=row.get("display_name"),
        avatar_url=row.get("avatar_url"),
        created_at=row.get("created_at"),
    )


# =============================================================================
# User Repository Functions
# =============================================================================


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    sql = text(
        """
        select id, email, password_hash, created_at, last_login_at
        from public.users
        where email = :email
        limit 1
        """
    )
    res = session.execute(sql, {"email": email}).mappings().first()
    if not res:
        return None
    return _row_to_user(res)


def get_user_by_id(session: Session, user_id: str) -> Optional[User]:
    sql = text(
        """
        select id, email, password_hash, created_at, last_login_at
        from public.users
        where id = :id
        limit 1
        """
    )
    res = session.execute(sql, {"id": user_id}).mappings().first()
    if not res:
        return None
    return _row_to_user(res)


def create_user(
    session: Session,
    email: str,
    password: str,
    commit: bool = True,
) -> User:
    """
    Create a new user with hashed password.

    Raises:
        EmailAlreadyExists if unique constraint violated.
    """
    # Pre-check to give cleaner error (avoid relying solely on DB exception)
    existing = get_user_by_email(session, email)
    if existing:
        raise EmailAlreadyExists(f"Email already exists: {email}")

    pwd_hash = hash_password(password)
    sql = text(
        """
        insert into public.users (email, password_hash)
        values (:email, :password_hash)
        returning id, email, password_hash, created_at, last_login_at
        """
    )
    try:
        row = session.execute(
            sql, {"email": email, "password_hash": pwd_hash}
        ).mappings().first()
        if commit:
            session.commit()
    except Exception as e:
        session.rollback()
        # Race condition: another insert slipped in
        if "duplicate key" in str(e).lower():
            raise EmailAlreadyExists(f"Email already exists: {email}") from e
        raise AuthRepositoryError(f"Failed to create user: {e}") from e

    if not row:
        raise AuthRepositoryError("Insert returned no row.")
    return _row_to_user(row)


def verify_user_credentials(
    session: Session,
    email: str,
    password: str,
    update_last_login: bool = True,
    commit: bool = True,
) -> Optional[User]:
    """
    Verify email/password. Returns User or None.
    Optionally updates last_login_at on success.
    """
    user = get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None

    if update_last_login:
        touch_user_last_login(session, user.id, commit=commit)
        # Refresh user object
        user = get_user_by_id(session, user.id) or user
    return user


def touch_user_last_login(session: Session, user_id: str, commit: bool = True) -> None:
    sql = text(
        """
        update public.users
        set last_login_at = now()
        where id = :id
        """
    )
    try:
        session.execute(sql, {"id": user_id})
        if commit:
            session.commit()
    except Exception as e:
        session.rollback()
        raise AuthRepositoryError(f"Failed to update last_login_at: {e}") from e


def list_users(
    session: Session,
    limit: int = 50,
    offset: int = 0,
) -> List[User]:
    sql = text(
        """
        select id, email, password_hash, created_at, last_login_at
        from public.users
        order by created_at desc
        limit :limit offset :offset
        """
    )
    rows = session.execute(sql, {"limit": limit, "offset": offset}).mappings().all()
    return [_row_to_user(r) for r in rows]


def delete_user(
    session: Session,
    user_id: str,
    commit: bool = True,
) -> bool:
    """
    Delete a user (cascades to profile due to FK).
    Returns True if a row was deleted.
    """
    sql = text("delete from public.users where id = :id")
    try:
        res = session.execute(sql, {"id": user_id})
        deleted = res.rowcount > 0
        if commit:
            session.commit()
        return deleted
    except Exception as e:
        session.rollback()
        raise AuthRepositoryError(f"Failed to delete user: {e}") from e


# =============================================================================
# Profile Repository Functions
# =============================================================================


def upsert_profile(
    session: Session,
    user_id: str,
    display_name: Optional[str],
    avatar_url: Optional[str],
    commit: bool = True,
) -> Profile:
    """
    Insert or update a profile for a user.
    Uses ON CONFLICT (user_id) DO UPDATE.
    """
    sql = text(
        """
        insert into public.profiles (user_id, display_name, avatar_url)
        values (:user_id, :display_name, :avatar_url)
        on conflict (user_id) do update
        set display_name = excluded.display_name,
            avatar_url   = excluded.avatar_url
        returning user_id, display_name, avatar_url, created_at
        """
    )
    try:
        row = session.execute(
            sql,
            {
                "user_id": user_id,
                "display_name": display_name,
                "avatar_url": avatar_url,
            },
        ).mappings().first()
        if commit:
            session.commit()
    except Exception as e:
        session.rollback()
        raise AuthRepositoryError(f"Failed to upsert profile: {e}") from e
    if not row:
        raise AuthRepositoryError("Upsert profile returned no row.")
    return _row_to_profile(row)


def get_profile(session: Session, user_id: str) -> Optional[Profile]:
    sql = text(
        """
        select user_id, display_name, avatar_url, created_at
        from public.profiles
        where user_id = :user_id
        limit 1
        """
    )
    row = session.execute(sql, {"user_id": user_id}).mappings().first()
    if not row:
        return None
    return _row_to_profile(row)


# =============================================================================
# Utility & Aggregation
# =============================================================================


def get_user_with_profile(
    session: Session,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Convenience aggregator returning combined user+profile dict.
    """
    user = get_user_by_id(session, user_id)
    if not user:
        return None
    profile = get_profile(session, user_id)
    return {
        "user": user,
        "profile": profile,
    }


def search_users_by_email_prefix(
    session: Session,
    prefix: str,
    limit: int = 20,
) -> List[User]:
    sql = text(
        """
        select id, email, password_hash, created_at, last_login_at
        from public.users
        where email ilike :pat
        order by email asc
        limit :limit
        """
    )
    rows = session.execute(
        sql, {"pat": f"{prefix}%", "limit": limit}
    ).mappings().all()
    return [_row_to_user(r) for r in rows]


# =============================================================================
# Bulk Helpers (Illustrative)
# =============================================================================


def bulk_get_users(
    session: Session,
    user_ids: Iterable[str],
) -> Dict[str, User]:
    """
    Fetch multiple users and return mapping {user_id: User}
    """
    ids = list({u for u in user_ids})
    if not ids:
        return {}
    sql = text(
        """
        select id, email, password_hash, created_at, last_login_at
        from public.users
        where id = any(:ids)
        """
    )
    rows = session.execute(sql, {"ids": ids}).mappings().all()
    return {str(r["id"]): _row_to_user(r) for r in rows}


# =============================================================================
# End of repository.py
# =============================================================================
