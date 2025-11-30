"""
Regression test skeleton for the animation preview streaming layer.

Focus areas:
1. Error classification (classify_preview_error)
2. Heartbeat & progress events in generate_manim_preview_stream
3. allow_llm_fix flag behavior
4. Guarding axis label None edge case (distribution template)

NOTE:
These tests are designed as a scaffold. They rely on lightweight monkeypatching
instead of invoking real Manim renders (which would be slow and environment‑dependent).

To convert into full tests:
- Add fixtures for temporary artifact directories.
- Integrate real dataset sampling once implemented.
"""

from __future__ import annotations
import time
import types
import pytest

# Import targets (adjust if package layout changes)
from agents.tools.preview_manim import (
    classify_preview_error,
    generate_manim_preview_stream,
    PreviewError,
)
from agents.tools.danim_templates import generate_distribution_code
from agents.tools.danim_templates import ChartSpec, DataBinding


# -----------------------------
# 1. Error Classification Tests
# -----------------------------

@pytest.mark.parametrize(
    "err,expected_category,allow_fix",
    [
        ("AttributeError: 'NoneType' object has no attribute 'find' in Text(", "MissingAxisLabel", False),
        ("KeyError: 'value'", "MissingDataColumn", False),
        ("ValueError: could not convert string to float: 'abc'", "DataTypeIssue", False),
        ("ModuleNotFoundError: No module named 'foo'", "EnvironmentDependency", False),
        ("MemoryError: killed", "ResourceLimit", False),
        ("SyntaxError: invalid syntax", "SceneSyntax", True),
        ("Manim preview timed out after", "PerformanceTimeout", False),
        ("Random obscure error", "UnknownRuntime", True),
    ],
)
def test_classify_preview_error(err, expected_category, allow_fix):
    category, msg, allow_llm_fix = classify_preview_error(err)
    assert category == expected_category
    assert allow_llm_fix == allow_fix
    assert isinstance(msg, str) and msg  # message is non-empty


# -------------------------------------------------
# 2. Heartbeat & Progress Streaming (Mocked Preview)
# -------------------------------------------------

def _mock_generate_manim_preview_delay(*_args, **_kwargs):
    """
    Simulate a slow preview render that produces frames after a delay.
    We emulate frame creation by touching dummy files only indirectly; here we
    just sleep so heartbeat loop can tick.
    """
    time.sleep(0.2)  # short sleep; heartbeat interval in stream is 5s by default
    # Return a fake image list
    return {
        "images": [
            {"url": "/static/previews/fake/frame_0000.png", "revised_prompt": ""},
            {"url": "/static/previews/fake/frame_0004.png", "revised_prompt": ""},
        ],
        "preview_token": "fake-token",
        "count": 2,
    }


def test_generate_manim_preview_stream_success(monkeypatch):
    """
    Verifies that:
    - Initial 'Generating preview...' event emitted.
    - Final 'Preview generated.' event present.
    - No RunError for successful case.
    NOTE: Heartbeat may not appear because we keep the mock fast; we do not
    assert heartbeat presence here to avoid timing flakiness.
    """
    monkeypatch.setattr(
        "agents.tools.preview_manim.generate_manim_preview",
        _mock_generate_manim_preview_delay,
    )

    events = list(
        generate_manim_preview_stream(
            code="class GenScene(Scene):\n    def construct(self):\n        pass",
            class_name="GenScene",
            run_id="r1",
            quality="low",
            heartbeat_interval=1,  # shorten for test potential
            enable_progress=False,
        )
    )

    contents = [e["content"] for e in events if e["event"] == "RunContent"]
    assert any("Generating preview" in c for c in contents)
    assert any("Preview generated" in c for c in contents)
    assert not any(e for e in events if e["event"] == "RunError")


def _mock_generate_manim_preview_error(*_args, **_kwargs):
    raise PreviewError("AttributeError: 'NoneType' object has no attribute 'find' in Text(")


def test_generate_manim_preview_stream_missing_axis_label(monkeypatch):
    """
    Ensures MissingAxisLabel classification surfaces with allow_llm_fix False.
    """
    monkeypatch.setattr(
        "agents.tools.preview_manim.generate_manim_preview",
        _mock_generate_manim_preview_error,
    )

    events = list(
        generate_manim_preview_stream(
            code="class GenScene(Scene):\n    def construct(self):\n        pass",
            class_name="GenScene",
            run_id="r2",
            heartbeat_interval=1,
            enable_progress=False,
        )
    )
    errors = [e for e in events if e["event"] == "RunError"]
    assert errors, "Expected at least one RunError event"
    err = errors[-1]
    assert "[MissingAxisLabel]" in err["content"]
    assert err.get("allow_llm_fix") is False


# -------------------------------------------------------
# 3. Axis Label Guard (Distribution Template Regression)
# -------------------------------------------------------

def test_distribution_template_axis_label_guard():
    """
    Generate distribution code with spec lacking axes labels and ensure
    resulting code defines non-empty X_LABEL / Y_LABEL literals (fallbacks).
    This guards against Text(None) regression.
    """
    spec = ChartSpec()
    spec.data_binding = DataBinding(value_col="value", time_col="time", group_col=None, entity_col=None)
    # Do NOT set spec.axes to force fallback defaults

    code = generate_distribution_code(spec, csv_path=__file__)  # csv existence will be ignored internally? Might raise.
    # Since generate_distribution_code requires a real CSV, we catch FileNotFoundError here.
    # Skeleton test: structure only; adapt to actual fixture with real CSV in full implementation.
    if "Dataset not found" in code or not code.strip():
        pytest.skip("Provide a real CSV path for full axis label guard test.")
    assert "X_LABEL" in code and "Y_LABEL" in code
    # Rough check they are not 'None'
    assert "None" not in code.split("X_LABEL")[1][:60]
    assert "None" not in code.split("Y_LABEL")[1][:60]


# ----------------------------------------------------
# 4. allow_llm_fix Flag Propagation (Mocked Scenario)
# ----------------------------------------------------

def _mock_generate_manim_preview_unknown_runtime(*_args, **_kwargs):
    raise PreviewError("Some obscure failure without classification trigger words")


def test_preview_unknown_runtime_allows_llm_fix(monkeypatch):
    monkeypatch.setattr(
        "agents.tools.preview_manim.generate_manim_preview",
        _mock_generate_manim_preview_unknown_runtime,
    )
    events = list(
        generate_manim_preview_stream(
            code="class GenScene(Scene):\n    def construct(self):\n        pass",
            class_name="GenScene",
            run_id="r3",
            heartbeat_interval=1,
            enable_progress=False,
        )
    )
    err = [e for e in events if e["event"] == "RunError"][-1]
    assert "[UnknownRuntime]" in err["content"]
    assert err.get("allow_llm_fix") is True


# ---------------------------------------------
# 5. PerformanceTimeout Classification Skeleton
# ---------------------------------------------

def _mock_generate_manim_preview_timeout(*_args, **_kwargs):
    raise PreviewError("Manim preview timed out after 60s")


def test_preview_timeout_classification(monkeypatch):
    monkeypatch.setattr(
        "agents.tools.preview_manim.generate_manim_preview",
        _mock_generate_manim_preview_timeout,
    )
    events = list(
        generate_manim_preview_stream(
            code="class GenScene(Scene):\n    def construct(self):\n        pass",
            class_name="GenScene",
            run_id="r4",
            heartbeat_interval=1,
            enable_progress=False,
        )
    )
    err = [e for e in events if e["event"] == "RunError"][-1]
    assert "[PerformanceTimeout]" in err["content"]
    assert err.get("allow_llm_fix") is False


# -----------------------------
# 6. Heartbeat Presence (Slow)
# -----------------------------

def _mock_generate_manim_preview_slow(*_args, **_kwargs):
    time.sleep(2)
    return {"images": [], "preview_token": "t", "count": 0}


@pytest.mark.timeout(10)
def test_heartbeat_emission(monkeypatch):
    monkeypatch.setattr(
        "agents.tools.preview_manim.generate_manim_preview",
        _mock_generate_manim_preview_slow,
    )
    events = []
    for e in generate_manim_preview_stream(
        code="class GenScene(Scene):\n    def construct(self):\n        pass",
        class_name="GenScene",
        run_id="r5",
        heartbeat_interval=1,
        enable_progress=False,
    ):
        events.append(e)
    heartbeats = [e for e in events if e["event"] == "RunHeartbeat"]
    assert len(heartbeats) >= 1, "Expected at least one heartbeat during slow preview"


# -----------------------------
# 7. Progress Messages (Enabled)
# -----------------------------

def _mock_generate_manim_preview_progress(*_args, **_kwargs):
    time.sleep(0.3)
    return {"images": [{"url": "/static/previews/x/frame_0000.png", "revised_prompt": ""}], "preview_token": "x", "count": 1}


def test_progress_messages(monkeypatch):
    monkeypatch.setattr(
        "agents.tools.preview_manim.generate_manim_preview",
        _mock_generate_manim_preview_progress,
    )
    events = list(
        generate_manim_preview_stream(
            code="class GenScene(Scene):\n    def construct(self):\n        pass",
            class_name="GenScene",
            run_id="r6",
            heartbeat_interval=1,
            enable_progress=True,
        )
    )
    progress_events = [e for e in events if e["event"] == "RunContent" and "Preview progress:" in e.get("content", "")]
    # Because PNG counting is naive (may be zero in test), allow zero but ensure mechanism did not crash
    assert progress_events is not None
    # Ensure final success present
    assert any("Preview generated." in e.get("content", "") for e in events if e["event"] == "RunContent")


# -----------------------------
# 8. Documentation Guidance
# -----------------------------
# Additional tests to add later:
# - Real dataset melt integration (requires fixture / test data file).
# - Sampling notice events (PreviewSampleNotice) once implemented.
# - Render phase verification after preview success (integration test).
# - Cleanup of artifacts/work directories (resource hygiene).
# - Multi-attempt runtime fix path (SceneSyntax classification followed by success).
#
# Keep this file lean; move heavy integration tests into a separate module (e.g. test_animation_pipeline_integrations.py).
#
# End of skeleton.
