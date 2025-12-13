"""
Unit tests for the session_context module.

Tests cover:
- Creating and retrieving session context
- Updating existing context with merge behavior
- TTL expiration handling
- Edge cases (None session_id, etc.)
"""

import time
import pytest
from api.session_context import (
    AnimationContext,
    get_session_context,
    update_session_context,
    clear_session_context,
    get_all_contexts,
    get_context_count,
    force_cleanup,
    DEFAULT_TTL_SECONDS,
    _context_store,
    _context_lock,
)


@pytest.fixture(autouse=True)
def cleanup_context_store():
    """Clean up the context store before and after each test."""
    with _context_lock:
        _context_store.clear()
    yield
    with _context_lock:
        _context_store.clear()


class TestAnimationContext:
    """Tests for the AnimationContext dataclass."""

    def test_default_values(self):
        ctx = AnimationContext()
        assert ctx.csv_path is None
        assert ctx.chart_type is None
        assert ctx.data_binding == {}
        assert not ctx.is_expired()
        assert not ctx.has_dataset()

    def test_has_dataset_with_csv_path(self):
        ctx = AnimationContext(csv_path="/path/to/data.csv")
        assert ctx.has_dataset()

    def test_has_dataset_with_melted_path(self):
        ctx = AnimationContext(melted_dataset_path="/path/to/melted.csv")
        assert ctx.has_dataset()

    def test_get_effective_csv_path_prefers_melted(self):
        ctx = AnimationContext(
            csv_path="/path/to/original.csv",
            melted_dataset_path="/path/to/melted.csv"
        )
        assert ctx.get_effective_csv_path() == "/path/to/melted.csv"

    def test_get_effective_csv_path_fallback_to_csv_path(self):
        ctx = AnimationContext(csv_path="/path/to/data.csv")
        assert ctx.get_effective_csv_path() == "/path/to/data.csv"

    def test_merge_updates_non_none_values(self):
        ctx = AnimationContext(
            csv_path="/old/path.csv",
            chart_type="bubble",
        )
        ctx.merge(chart_type="distribution", aspect_ratio="16:9")
        assert ctx.csv_path == "/old/path.csv"  # Not changed (None not passed)
        assert ctx.chart_type == "distribution"  # Updated
        assert ctx.aspect_ratio == "16:9"  # Updated

    def test_merge_preserves_none_updates(self):
        ctx = AnimationContext(csv_path="/path.csv", chart_type="bubble")
        ctx.merge(chart_type=None)  # Should NOT overwrite with None
        assert ctx.chart_type == "bubble"

    def test_merge_data_binding_is_merged(self):
        ctx = AnimationContext(
            data_binding={"group_col": "country", "time_col": "year"}
        )
        ctx.merge(data_binding={"value_col": "population"})
        assert ctx.data_binding == {
            "group_col": "country",
            "time_col": "year",
            "value_col": "population",
        }

    def test_is_expired(self):
        ctx = AnimationContext()
        ctx.expires_at = time.time() - 1  # Set to past
        assert ctx.is_expired()

    def test_refresh_ttl(self):
        ctx = AnimationContext()
        old_expires = ctx.expires_at
        time.sleep(0.01)
        ctx.refresh_ttl()
        assert ctx.expires_at > old_expires

    def test_to_dict(self):
        ctx = AnimationContext(csv_path="/path.csv", chart_type="bubble")
        d = ctx.to_dict()
        assert isinstance(d, dict)
        assert d["csv_path"] == "/path.csv"
        assert d["chart_type"] == "bubble"


class TestSessionContextFunctions:
    """Tests for the session context store functions."""

    def test_get_session_context_none_session_id(self):
        result = get_session_context(None)
        assert result is None

    def test_get_session_context_empty_string_session_id(self):
        result = get_session_context("")
        assert result is None

    def test_get_session_context_not_found(self):
        result = get_session_context("nonexistent-session")
        assert result is None

    def test_update_session_context_creates_new(self):
        session_id = "test-session-1"
        ctx = update_session_context(
            session_id=session_id,
            csv_path="/static/datasets/test.csv",
            chart_type="bubble",
        )
        assert ctx is not None
        assert ctx.csv_path == "/static/datasets/test.csv"
        assert ctx.chart_type == "bubble"

    def test_update_session_context_none_session_id(self):
        result = update_session_context(session_id=None, csv_path="/path.csv")
        assert result is None

    def test_get_session_context_retrieves_stored(self):
        session_id = "test-session-2"
        update_session_context(
            session_id=session_id,
            csv_path="/static/datasets/test.csv",
        )
        ctx = get_session_context(session_id)
        assert ctx is not None
        assert ctx.csv_path == "/static/datasets/test.csv"

    def test_update_session_context_merges_existing(self):
        session_id = "test-session-3"
        # First update
        update_session_context(
            session_id=session_id,
            csv_path="/static/datasets/test.csv",
            chart_type="bubble",
        )
        # Second update - only change chart_type
        update_session_context(
            session_id=session_id,
            chart_type="distribution",
        )
        ctx = get_session_context(session_id)
        assert ctx.csv_path == "/static/datasets/test.csv"  # Still there
        assert ctx.chart_type == "distribution"  # Updated

    def test_clear_session_context(self):
        session_id = "test-session-4"
        update_session_context(session_id=session_id, csv_path="/path.csv")
        assert get_session_context(session_id) is not None

        result = clear_session_context(session_id)
        assert result is True
        assert get_session_context(session_id) is None

    def test_clear_session_context_nonexistent(self):
        result = clear_session_context("nonexistent")
        assert result is False

    def test_clear_session_context_none_session_id(self):
        result = clear_session_context(None)
        assert result is False

    def test_get_all_contexts(self):
        update_session_context(session_id="sess-a", csv_path="/a.csv")
        update_session_context(session_id="sess-b", csv_path="/b.csv")

        all_ctx = get_all_contexts()
        assert len(all_ctx) == 2
        assert "sess-a" in all_ctx
        assert "sess-b" in all_ctx

    def test_get_context_count(self):
        assert get_context_count() == 0
        update_session_context(session_id="sess-1", csv_path="/1.csv")
        assert get_context_count() == 1
        update_session_context(session_id="sess-2", csv_path="/2.csv")
        assert get_context_count() == 2

    def test_expired_context_not_returned(self):
        session_id = "test-session-expired"
        ctx = update_session_context(
            session_id=session_id,
            csv_path="/path.csv",
            ttl_seconds=0.001,  # Very short TTL
        )
        time.sleep(0.01)  # Wait for expiration
        result = get_session_context(session_id)
        assert result is None

    def test_force_cleanup(self):
        session_id = "test-session-cleanup"
        update_session_context(
            session_id=session_id,
            csv_path="/path.csv",
            ttl_seconds=0.001,
        )
        time.sleep(0.01)  # Wait for expiration

        # Force cleanup should remove expired
        removed = force_cleanup()
        assert removed >= 1
        assert get_context_count() == 0

    def test_ttl_refresh_on_access(self):
        session_id = "test-session-refresh"
        ctx = update_session_context(
            session_id=session_id,
            csv_path="/path.csv",
        )
        old_expires = ctx.expires_at
        time.sleep(0.01)

        # Access the context
        retrieved = get_session_context(session_id)
        assert retrieved is not None
        assert retrieved.expires_at > old_expires


class TestDataBindingMerge:
    """Tests for data binding merge behavior."""

    def test_data_binding_merges_correctly(self):
        session_id = "test-binding-merge"

        # First update with group and time
        update_session_context(
            session_id=session_id,
            data_binding={"group_col": "country", "time_col": "year"},
        )

        # Second update adds value_col
        update_session_context(
            session_id=session_id,
            data_binding={"value_col": "population"},
        )

        ctx = get_session_context(session_id)
        assert ctx.data_binding["group_col"] == "country"
        assert ctx.data_binding["time_col"] == "year"
        assert ctx.data_binding["value_col"] == "population"

    def test_data_binding_overwrites_on_new_value(self):
        session_id = "test-binding-overwrite"

        update_session_context(
            session_id=session_id,
            data_binding={"group_col": "country"},
        )

        update_session_context(
            session_id=session_id,
            data_binding={"group_col": "region"},  # Overwrite
        )

        ctx = get_session_context(session_id)
        assert ctx.data_binding["group_col"] == "region"


class TestConcurrency:
    """Basic concurrency tests."""

    def test_concurrent_updates(self):
        """Test that concurrent updates don't cause issues."""
        import threading

        session_id = "test-concurrent"
        errors = []

        def updater(i):
            try:
                for _ in range(10):
                    update_session_context(
                        session_id=session_id,
                        csv_path=f"/path/{i}.csv",
                    )
                    get_session_context(session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=updater, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Context should still be accessible
        ctx = get_session_context(session_id)
        assert ctx is not None
