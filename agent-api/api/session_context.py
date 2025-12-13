"""
Session-level context store for the animation pipeline.

This module provides in-memory persistence of animation context across
multiple messages within a session. When a user uploads a dataset or
provides chart preferences, this context is stored and can be retrieved
on subsequent messages even if those messages don't include the csv_path.

Key Features:
- Store csv_path, chart_type, data bindings, and other preferences per session
- Automatic TTL-based expiration to prevent memory leaks
- Thread-safe operations for concurrent request handling
- Optional merging of partial updates

Usage:
    from api.session_context import (
        get_session_context,
        update_session_context,
        clear_session_context,
    )

    # Store context when user uploads a dataset
    update_session_context(session_id, csv_path="/static/datasets/data.csv")

    # Retrieve context on subsequent messages
    ctx = get_session_context(session_id)
    if ctx and ctx.csv_path:
        # Use the stored csv_path
        ...
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


logger = logging.getLogger(__name__)

# Default TTL: 2 hours (sessions typically don't last longer)
DEFAULT_TTL_SECONDS = 2 * 60 * 60

# Cleanup interval: run cleanup every 5 minutes
CLEANUP_INTERVAL_SECONDS = 5 * 60


@dataclass
class AnimationContext:
    """
    Stores animation-related context for a session.

    Attributes:
        csv_path: The resolved filesystem path or /static/... URL path to the dataset
        original_csv_path: The original path as provided by the user/frontend
        chart_type: Inferred or user-selected chart type (bubble, distribution, etc.)
        data_binding: Column mappings (group_col, time_col, value_col, etc.)
        creation_mode: For bubble charts, the creation mode (1, 2, or 3)
        aspect_ratio: Video aspect ratio preference (16:9, 9:16, 1:1)
        render_quality: Render quality preference (low, medium, high)
        melted_dataset_path: Path to the melted/transformed dataset if applicable
        user_preferences: Any additional user preferences as a dict
        last_intent_message: The last message that indicated animation intent
        created_at: Timestamp when the context was first created
        updated_at: Timestamp when the context was last updated
        expires_at: Timestamp when the context should expire
    """
    csv_path: Optional[str] = None
    original_csv_path: Optional[str] = None
    chart_type: Optional[str] = None
    data_binding: Dict[str, Optional[str]] = field(default_factory=dict)
    creation_mode: Optional[int] = None
    aspect_ratio: Optional[str] = None
    render_quality: Optional[str] = None
    melted_dataset_path: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    last_intent_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + DEFAULT_TTL_SECONDS)

    def is_expired(self) -> bool:
        """Check if this context has expired."""
        return time.time() > self.expires_at

    def refresh_ttl(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        """Extend the expiration time."""
        self.expires_at = time.time() + ttl_seconds
        self.updated_at = time.time()

    def has_dataset(self) -> bool:
        """Check if a dataset path is available."""
        return bool(self.csv_path or self.melted_dataset_path)

    def get_effective_csv_path(self) -> Optional[str]:
        """Get the best available dataset path (prefer melted if available)."""
        return self.melted_dataset_path or self.csv_path

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return asdict(self)

    def merge(self, **kwargs) -> None:
        """
        Merge partial updates into this context.
        Only non-None values are applied.
        """
        for key, value in kwargs.items():
            if value is not None and hasattr(self, key):
                if key == "data_binding" and isinstance(value, dict):
                    # Merge data_binding dict instead of replacing
                    for k, v in value.items():
                        if v is not None:
                            self.data_binding[k] = v
                elif key == "user_preferences" and isinstance(value, dict):
                    # Merge user_preferences dict
                    self.user_preferences.update(value)
                else:
                    setattr(self, key, value)
        self.updated_at = time.time()


# Global registry and lock
_context_lock = threading.RLock()
_context_store: Dict[str, AnimationContext] = {}
_last_cleanup: float = 0.0


def _cleanup_expired() -> int:
    """
    Remove expired contexts from the store.
    Returns the number of contexts removed.
    Should be called with _context_lock held.
    """
    global _last_cleanup
    now = time.time()

    # Only run cleanup periodically
    if now - _last_cleanup < CLEANUP_INTERVAL_SECONDS:
        return 0

    _last_cleanup = now
    expired_keys = [k for k, v in _context_store.items() if v.is_expired()]

    for key in expired_keys:
        del _context_store[key]

    if expired_keys:
        logger.debug("Cleaned up %d expired session contexts", len(expired_keys))

    return len(expired_keys)


def get_session_context(session_id: Optional[str]) -> Optional[AnimationContext]:
    """
    Retrieve the animation context for a session.

    Args:
        session_id: The session identifier

    Returns:
        The AnimationContext if found and not expired, None otherwise
    """
    if not session_id:
        return None

    with _context_lock:
        _cleanup_expired()

        ctx = _context_store.get(session_id)
        if ctx is None:
            return None

        if ctx.is_expired():
            del _context_store[session_id]
            logger.debug("Session context %s expired, removed", session_id)
            return None

        # Refresh TTL on access
        ctx.refresh_ttl()
        return ctx


def update_session_context(
    session_id: Optional[str],
    csv_path: Optional[str] = None,
    original_csv_path: Optional[str] = None,
    chart_type: Optional[str] = None,
    data_binding: Optional[Dict[str, Optional[str]]] = None,
    creation_mode: Optional[int] = None,
    aspect_ratio: Optional[str] = None,
    render_quality: Optional[str] = None,
    melted_dataset_path: Optional[str] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    last_intent_message: Optional[str] = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
) -> Optional[AnimationContext]:
    """
    Update or create the animation context for a session.

    This function merges the provided values into the existing context,
    or creates a new context if one doesn't exist.

    Args:
        session_id: The session identifier
        csv_path: The resolved dataset path
        original_csv_path: The original path as provided
        chart_type: The chart type (bubble, distribution, etc.)
        data_binding: Column mappings dict
        creation_mode: Bubble chart creation mode
        aspect_ratio: Video aspect ratio
        render_quality: Render quality setting
        melted_dataset_path: Path to melted dataset
        user_preferences: Additional preferences dict
        last_intent_message: The message that triggered the update
        ttl_seconds: Time-to-live for this context

    Returns:
        The updated AnimationContext, or None if session_id is invalid
    """
    if not session_id:
        return None

    with _context_lock:
        _cleanup_expired()

        ctx = _context_store.get(session_id)

        if ctx is None or ctx.is_expired():
            # Create new context
            ctx = AnimationContext(
                csv_path=csv_path,
                original_csv_path=original_csv_path or csv_path,
                chart_type=chart_type,
                data_binding=data_binding or {},
                creation_mode=creation_mode,
                aspect_ratio=aspect_ratio,
                render_quality=render_quality,
                melted_dataset_path=melted_dataset_path,
                user_preferences=user_preferences or {},
                last_intent_message=last_intent_message,
            )
            ctx.refresh_ttl(ttl_seconds)
            _context_store[session_id] = ctx
            logger.debug("Created new session context for %s", session_id)
        else:
            # Merge into existing context
            ctx.merge(
                csv_path=csv_path,
                original_csv_path=original_csv_path,
                chart_type=chart_type,
                data_binding=data_binding,
                creation_mode=creation_mode,
                aspect_ratio=aspect_ratio,
                render_quality=render_quality,
                melted_dataset_path=melted_dataset_path,
                user_preferences=user_preferences,
                last_intent_message=last_intent_message,
            )
            ctx.refresh_ttl(ttl_seconds)
            logger.debug("Updated session context for %s", session_id)

        return ctx


def clear_session_context(session_id: Optional[str]) -> bool:
    """
    Remove the animation context for a session.

    Args:
        session_id: The session identifier

    Returns:
        True if a context was removed, False otherwise
    """
    if not session_id:
        return False

    with _context_lock:
        if session_id in _context_store:
            del _context_store[session_id]
            logger.debug("Cleared session context for %s", session_id)
            return True
        return False


def get_all_contexts() -> Dict[str, dict]:
    """
    Get all active (non-expired) session contexts.
    Primarily for debugging/monitoring.

    Returns:
        Dict mapping session_id to context dict
    """
    with _context_lock:
        _cleanup_expired()
        return {
            session_id: ctx.to_dict()
            for session_id, ctx in _context_store.items()
            if not ctx.is_expired()
        }


def get_context_count() -> int:
    """
    Get the number of active session contexts.

    Returns:
        Number of non-expired contexts
    """
    with _context_lock:
        _cleanup_expired()
        return len(_context_store)


def force_cleanup() -> int:
    """
    Force cleanup of expired contexts (bypasses the interval check).

    Returns:
        Number of contexts removed
    """
    global _last_cleanup
    with _context_lock:
        _last_cleanup = 0  # Reset to force cleanup
        return _cleanup_expired()
