"""
Comprehensive Pipeline Logger for Animation Engine

This module provides structured logging throughout the animation pipeline,
from data submission to final animation generation. It captures every step
with detailed context for debugging issues, especially LLM fallback scenarios.

Usage:
    from api.pipeline_logger import PipelineLogger, PipelineStep

    logger = PipelineLogger(run_id="abc-123", session_id="sess-456")
    logger.step(PipelineStep.DATA_UPLOAD, "CSV file received", {"filename": "data.csv", "size": 1024})
    logger.error(PipelineStep.CODE_GENERATION, "LLM timeout", {"engine": "anthropic", "model": "claude-sonnet"})
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, List
from functools import wraps

# Configure root logger for pipeline
_pipeline_logger = logging.getLogger("animation_pipeline")
_pipeline_logger.setLevel(logging.DEBUG)

# Ensure we have a handler
if not _pipeline_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    _pipeline_logger.addHandler(handler)


class PipelineStep(str, Enum):
    """Enumeration of all pipeline steps for tracing."""

    # Request handling
    REQUEST_RECEIVED = "request_received"
    REQUEST_VALIDATED = "request_validated"

    # Intent detection
    INTENT_DETECTION_START = "intent_detection_start"
    INTENT_DETECTION_COMPLETE = "intent_detection_complete"
    INTENT_DETECTION_ERROR = "intent_detection_error"

    # Data handling
    DATA_UPLOAD = "data_upload"
    DATA_VALIDATION = "data_validation"
    DATA_PREPROCESSING = "data_preprocessing"
    DATA_MELT = "data_melt"
    DATA_BINDING = "data_binding"

    # Chart inference
    CHART_INFERENCE_START = "chart_inference_start"
    CHART_INFERENCE_COMPLETE = "chart_inference_complete"
    CHART_INFERENCE_ERROR = "chart_inference_error"

    # Spec generation
    SPEC_INFERENCE_START = "spec_inference_start"
    SPEC_INFERENCE_COMPLETE = "spec_inference_complete"
    SPEC_INFERENCE_ERROR = "spec_inference_error"

    # Template selection
    TEMPLATE_SELECTION_START = "template_selection_start"
    TEMPLATE_SELECTED = "template_selected"
    TEMPLATE_GENERATION = "template_generation"
    TEMPLATE_ERROR = "template_error"
    NO_TEMPLATE_MATCH = "no_template_match"

    # LLM Code generation (fallback)
    LLM_FALLBACK_START = "llm_fallback_start"
    LLM_API_CALL_START = "llm_api_call_start"
    LLM_API_CALL_COMPLETE = "llm_api_call_complete"
    LLM_API_CALL_ERROR = "llm_api_call_error"
    CODE_GENERATION_START = "code_generation_start"
    CODE_GENERATION_COMPLETE = "code_generation_complete"
    CODE_GENERATION_ERROR = "code_generation_error"
    CODE_GENERATION_TIMEOUT = "code_generation_timeout"

    # Code validation
    CODE_VALIDATION_START = "code_validation_start"
    CODE_VALIDATION_PASS = "code_validation_pass"
    CODE_VALIDATION_FAIL = "code_validation_fail"
    CODE_AUTO_FIX_START = "code_auto_fix_start"
    CODE_AUTO_FIX_COMPLETE = "code_auto_fix_complete"
    CODE_AUTO_FIX_ERROR = "code_auto_fix_error"

    # Preview generation
    PREVIEW_START = "preview_start"
    PREVIEW_FRAME_GENERATED = "preview_frame_generated"
    PREVIEW_COMPLETE = "preview_complete"
    PREVIEW_ERROR = "preview_error"

    # Render
    RENDER_START = "render_start"
    RENDER_PROGRESS = "render_progress"
    RENDER_COMPLETE = "render_complete"
    RENDER_ERROR = "render_error"

    # Export/Merge
    EXPORT_START = "export_start"
    EXPORT_PROGRESS = "export_progress"
    EXPORT_COMPLETE = "export_complete"
    EXPORT_ERROR = "export_error"

    # Run lifecycle
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"


@dataclass
class LogEntry:
    """Structured log entry for pipeline events."""

    timestamp: str
    step: str
    level: str
    message: str
    run_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class PipelineLogger:
    """
    Structured logger for the animation pipeline.

    Provides step-by-step logging with context, timing, and error tracking.
    Each run gets its own logger instance for isolated tracing.
    """

    def __init__(
        self,
        run_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.run_id = run_id
        self.session_id = session_id
        self.user_id = user_id
        self._step_timers: Dict[str, float] = {}
        self._entries: List[LogEntry] = []
        self._logger = _pipeline_logger

    def _create_entry(
        self,
        step: PipelineStep,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        tb: Optional[str] = None,
    ) -> LogEntry:
        """Create a structured log entry."""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            step=step.value,
            level=level,
            message=message,
            run_id=self.run_id,
            session_id=self.session_id,
            user_id=self.user_id,
            context=context or {},
            duration_ms=duration_ms,
            error=error,
            traceback=tb,
        )
        self._entries.append(entry)
        return entry

    def _log(self, entry: LogEntry):
        """Write log entry to the underlying logger."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        level = level_map.get(entry.level.upper(), logging.INFO)

        # Format: [STEP] message | context
        context_str = ""
        if entry.context:
            context_str = f" | {json.dumps(entry.context, default=str)}"

        duration_str = ""
        if entry.duration_ms is not None:
            duration_str = f" | duration={entry.duration_ms:.2f}ms"

        run_str = f"[run={entry.run_id}] " if entry.run_id else ""

        log_msg = f"{run_str}[{entry.step}] {entry.message}{duration_str}{context_str}"

        if entry.error:
            log_msg += f" | ERROR: {entry.error}"

        self._logger.log(level, log_msg)

        # Also log traceback if present
        if entry.traceback:
            self._logger.log(level, f"Traceback:\n{entry.traceback}")

    def debug(
        self,
        step: PipelineStep,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log a debug message."""
        entry = self._create_entry(step, "DEBUG", message, context)
        self._log(entry)

    def info(
        self,
        step: PipelineStep,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log an info message."""
        entry = self._create_entry(step, "INFO", message, context)
        self._log(entry)

    def step(
        self,
        step: PipelineStep,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Alias for info() - log a pipeline step."""
        self.info(step, message, context)

    def warning(
        self,
        step: PipelineStep,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log a warning message."""
        entry = self._create_entry(step, "WARNING", message, context)
        self._log(entry)

    def error(
        self,
        step: PipelineStep,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ):
        """Log an error message with optional exception details."""
        error_str = str(exception) if exception else None
        tb = traceback.format_exc() if exception else None

        # Don't include "NoneType: None" traceback
        if tb and "NoneType: None" in tb:
            tb = None

        entry = self._create_entry(
            step, "ERROR", message, context,
            error=error_str, tb=tb
        )
        self._log(entry)

    def critical(
        self,
        step: PipelineStep,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ):
        """Log a critical error."""
        error_str = str(exception) if exception else None
        tb = traceback.format_exc() if exception else None

        if tb and "NoneType: None" in tb:
            tb = None

        entry = self._create_entry(
            step, "CRITICAL", message, context,
            error=error_str, tb=tb
        )
        self._log(entry)

    def start_timer(self, step: PipelineStep):
        """Start a timer for a step (for measuring duration)."""
        self._step_timers[step.value] = time.time()

    def stop_timer(self, step: PipelineStep) -> Optional[float]:
        """Stop a timer and return duration in milliseconds."""
        start = self._step_timers.pop(step.value, None)
        if start is not None:
            return (time.time() - start) * 1000
        return None

    def step_with_duration(
        self,
        step: PipelineStep,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log a step with duration (must have called start_timer first)."""
        duration = self.stop_timer(step)
        entry = self._create_entry(step, "INFO", message, context, duration_ms=duration)
        self._log(entry)

    def get_entries(self) -> List[Dict[str, Any]]:
        """Get all log entries as dictionaries."""
        return [e.to_dict() for e in self._entries]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the pipeline run."""
        errors = [e for e in self._entries if e.level == "ERROR"]
        warnings = [e for e in self._entries if e.level == "WARNING"]

        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "total_steps": len(self._entries),
            "errors": len(errors),
            "warnings": len(warnings),
            "error_details": [{"step": e.step, "message": e.message, "error": e.error} for e in errors],
            "steps_executed": list(dict.fromkeys(e.step for e in self._entries)),
        }


# Global logger registry for accessing loggers by run_id
_logger_registry: Dict[str, PipelineLogger] = {}


def get_pipeline_logger(
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> PipelineLogger:
    """
    Get or create a pipeline logger for a run.

    If run_id is provided and a logger exists, return it.
    Otherwise, create a new logger.
    """
    if run_id and run_id in _logger_registry:
        return _logger_registry[run_id]

    logger = PipelineLogger(run_id=run_id, session_id=session_id, user_id=user_id)

    if run_id:
        _logger_registry[run_id] = logger

    return logger


def cleanup_logger(run_id: str):
    """Remove a logger from the registry (call after run completes)."""
    _logger_registry.pop(run_id, None)


def log_step(step: PipelineStep, message: str = ""):
    """
    Decorator for logging function entry/exit with timing.

    Usage:
        @log_step(PipelineStep.CODE_GENERATION_START, "Generating Manim code")
        def generate_code(prompt: str, run_id: str) -> str:
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to extract run_id from kwargs or first arg
            run_id = kwargs.get("run_id")
            if not run_id and args:
                # Check if first arg has run_id attribute
                first_arg = args[0]
                if hasattr(first_arg, "run_id"):
                    run_id = first_arg.run_id

            logger = get_pipeline_logger(run_id=run_id)
            func_name = func.__name__

            logger.start_timer(step)
            logger.debug(step, f"{message or func_name} started", {"function": func_name})

            try:
                result = func(*args, **kwargs)
                logger.step_with_duration(
                    step,
                    f"{message or func_name} completed",
                    {"function": func_name}
                )
                return result
            except Exception as e:
                logger.error(
                    step,
                    f"{message or func_name} failed",
                    {"function": func_name},
                    exception=e
                )
                raise

        return wrapper
    return decorator


# Convenience function for quick logging without creating a logger instance
def log_pipeline_event(
    step: PipelineStep,
    message: str,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    level: str = "INFO",
    context: Optional[Dict[str, Any]] = None,
    exception: Optional[Exception] = None,
):
    """
    Quick function to log a pipeline event without managing logger instances.

    Usage:
        log_pipeline_event(
            PipelineStep.LLM_FALLBACK_START,
            "Starting LLM fallback code generation",
            run_id="abc-123",
            context={"engine": "anthropic", "model": "claude-sonnet"}
        )
    """
    logger = get_pipeline_logger(run_id=run_id, session_id=session_id)

    level = level.upper()
    if level == "DEBUG":
        logger.debug(step, message, context)
    elif level == "INFO":
        logger.info(step, message, context)
    elif level == "WARNING":
        logger.warning(step, message, context)
    elif level == "ERROR":
        logger.error(step, message, context, exception)
    elif level == "CRITICAL":
        logger.critical(step, message, context, exception)
    else:
        logger.info(step, message, context)
