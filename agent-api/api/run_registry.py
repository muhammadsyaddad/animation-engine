"""
Global run registry for tracking long-running operations (preview, render, export)
and supporting user-initiated cancellation.

This module provides:
- RunState: lifecycle states for a run
- RunInfo / ProcessInfo: data structures for run/process tracking
- create_run(), set_state(), update_message(), get_run(), list_runs()
- register_temp_path(), register_artifact()
- add_process() to attach an externally-created subprocess to a run
- start_tracked_process() to spawn a subprocess with a new process group/session
- cancel_run() to gracefully terminate a run's processes (and force-kill if needed)
- remove_run() to purge registry entries

Notes:
- On POSIX systems, cancellation targets the entire process group (killpg) when available.
- On Windows, cancellation uses terminate()/kill() on each process.
- Callers should prefer start_tracked_process() to ensure processes can be canceled
  as a group. If you must create Popen yourself, call add_process() promptly so
  the registry can capture pid/pgid information.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class RunState(Enum):
    CREATED = auto()
    STARTING = auto()
    PREVIEWING = auto()
    RENDERING = auto()
    EXPORTING = auto()
    COMPLETED = auto()
    ERROR = auto()
    CANCELED = auto()


@dataclass
class ProcessInfo:
    """Information about a subprocess associated with a run."""
    role: str  # e.g., "preview", "render", "export", "worker"
    pid: int
    pgid: Optional[int] = None
    created_at: float = field(default_factory=lambda: time.time())
    # popen is optional; may be absent if we only know pid (e.g., restored state)
    popen: Optional[subprocess.Popen] = field(default=None, repr=False)

    def is_running(self) -> bool:
        try:
            if self.popen is not None:
                return self.popen.poll() is None
            # Fall back to os.kill with signal 0 on POSIX
            if os.name == "posix":
                os.kill(self.pid, 0)
                return True
            # On Windows without Popen, we can't reliably probe by pid; assume running
            return True
        except Exception:
            return False


@dataclass
class RunInfo:
    run_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    state: RunState = RunState.CREATED
    message: str = ""
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    error: Optional[str] = None

    # Tracking
    processes: Dict[str, ProcessInfo] = field(default_factory=dict)  # key by role or unique key
    temp_paths: List[str] = field(default_factory=list)              # work dirs to clean on cancel
    artifacts: List[str] = field(default_factory=list)               # produced outputs (retain)

    def to_dict(self) -> dict:
        d = asdict(self)
        # Serialize Enums
        d["state"] = self.state.name
        # Drop popen from process dict (not JSON-serializable)
        for k, v in self.processes.items():
            d["processes"][k] = {
                "role": v.role,
                "pid": v.pid,
                "pgid": v.pgid,
                "created_at": v.created_at,
                "running": v.is_running(),
            }
        return d


# Global registry and lock
_registry_lock = threading.RLock()
_registry: Dict[str, RunInfo] = {}


def _now() -> float:
    return time.time()


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


def generate_run_id() -> str:
    """Create a unique run identifier."""
    return str(uuid.uuid4())


def create_run(user_id: Optional[str] = None, session_id: Optional[str] = None, message: str = "") -> RunInfo:
    """Create and register a new run."""
    run_id = generate_run_id()
    info = RunInfo(run_id=run_id, user_id=user_id, session_id=session_id, message=message)
    with _registry_lock:
        _registry[run_id] = info
    logger.debug("Created run %s", run_id)
    return info


def get_run(run_id: str) -> Optional[RunInfo]:
    """Fetch a run by id."""
    with _registry_lock:
        return _registry.get(run_id)


def list_runs() -> List[dict]:
    """Return a list of run summaries as dictionaries."""
    with _registry_lock:
        return [info.to_dict() for info in _registry.values()]


def set_state(run_id: str, state: RunState, message: Optional[str] = None) -> None:
    """Update run state and optional message."""
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return
        info.state = state
        if message is not None:
            info.message = message
        info.updated_at = _now()
        if state in (RunState.STARTING, RunState.PREVIEWING, RunState.RENDERING, RunState.EXPORTING) and info.started_at is None:
            info.started_at = _now()
        if state in (RunState.COMPLETED, RunState.ERROR, RunState.CANCELED):
            info.ended_at = _now()
    logger.debug("Run %s set to %s (%s)", run_id, state.name, message or "")


def update_message(run_id: str, message: str) -> None:
    """Update run message without changing the state."""
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return
        info.message = message
        info.updated_at = _now()


def register_temp_path(run_id: str, path: str) -> None:
    """Register a path for cleanup on cancellation."""
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return
        if path and path not in info.temp_paths:
            info.temp_paths.append(path)


def register_artifact(run_id: str, path: str) -> None:
    """Register a produced artifact path (not auto-deleted)."""
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return
        if path and path not in info.artifacts:
            info.artifacts.append(path)


def add_process(run_id: str, popen: subprocess.Popen, role: str = "worker", key: Optional[str] = None) -> None:
    """
    Attach an existing subprocess to a run for later cancellation.

    key: optional unique key; defaults to role if not supplied (overwrites previous with same key)
    """
    if not popen or popen.pid is None:
        return

    pgid: Optional[int] = None
    if os.name == "posix":
        try:
            pgid = os.getpgid(popen.pid)
        except Exception:
            pgid = None

    proc_info = ProcessInfo(role=role, pid=popen.pid, pgid=pgid, popen=popen)
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return
        proc_key = key or role
        info.processes[proc_key] = proc_info
        info.updated_at = _now()
    logger.debug("Run %s added process pid=%s role=%s pgid=%s", run_id, popen.pid, role, pgid)


def start_tracked_process(
    run_id: str,
    cmd: List[str],
    role: str,
    cwd: Optional[str] = None,
    text: bool = True,
    bufsize: int = 1,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env: Optional[dict] = None,
    extra_creationflags: int = 0,
    start_new_session: Optional[bool] = None,
    **popen_kwargs,
) -> subprocess.Popen:
    """
    Spawn a subprocess configured for later cancellation and register it under the run.

    On POSIX: starts a new session/process group (setsid).
    On Windows: uses CREATE_NEW_PROCESS_GROUP flag so CTRL_BREAK/Kill can target the group.

    Returns the Popen instance.
    """
    if _is_windows():
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | int(extra_creationflags or 0)
        popen = subprocess.Popen(
            cmd,
            cwd=cwd,
            text=text,
            bufsize=bufsize,
            stdout=stdout,
            stderr=stderr,
            env=env,
            creationflags=creationflags,
            **popen_kwargs,
        )
    else:
        # For POSIX, explicitly start a new session unless caller overrides
        sns = True if start_new_session is None else bool(start_new_session)
        popen = subprocess.Popen(
            cmd,
            cwd=cwd,
            text=text,
            bufsize=bufsize,
            stdout=stdout,
            stderr=stderr,
            env=env,
            start_new_session=sns,
            **popen_kwargs,
        )

    add_process(run_id, popen, role=role)
    return popen


def _terminate_process(proc: ProcessInfo) -> None:
    """Send a graceful termination signal to a process or its group."""
    try:
        if _is_windows():
            # On Windows, try terminate(); kill() escalates if needed
            if proc.popen:
                proc.popen.terminate()
            else:
                # Without Popen, best effort is not straightforward; ignore
                pass
        else:
            # POSIX: prefer killing the process group
            if proc.pgid is not None:
                try:
                    os.killpg(proc.pgid, signal.SIGTERM)
                except ProcessLookupError:
                    return
            else:
                try:
                    os.kill(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    return
    except Exception as e:
        logger.debug("Error while terminating pid=%s: %s", proc.pid, e)


def _kill_process(proc: ProcessInfo) -> None:
    """Force kill a process or its group."""
    try:
        if _is_windows():
            if proc.popen:
                proc.popen.kill()
        else:
            if proc.pgid is not None:
                try:
                    os.killpg(proc.pgid, signal.SIGKILL)
                except ProcessLookupError:
                    return
            else:
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    return
    except Exception as e:
        logger.debug("Error while force-killing pid=%s: %s", proc.pid, e)


def cancel_run(run_id: str, reason: str = "user_canceled", grace_seconds: float = 5.0) -> bool:
    """
    Attempt to cancel a running job by terminating its processes.
    Returns True if the run moved to CANCELED (or was already finished), False if not found.

    Behavior:
    - Send graceful termination (SIGTERM / terminate) to all tracked processes.
    - Wait up to grace_seconds for exit.
    - Force kill remaining.
    - Clean up registered temp_paths.
    """
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return False

        # If already terminal state, nothing to do
        if info.state in (RunState.COMPLETED, RunState.ERROR, RunState.CANCELED):
            return True

        # Mark as canceling (message only for now)
        info.message = f"Cancel requested: {reason}"
        info.updated_at = _now()

        # Snapshot processes to operate outside of lock
        procs = list(info.processes.values())

    # Step 1: graceful termination
    for p in procs:
        _terminate_process(p)

    # Step 2: wait for them to exit up to grace period
    end_by = time.time() + float(grace_seconds or 0)
    for p in procs:
        if p.popen is None:
            continue
        remaining = end_by - time.time()
        if remaining <= 0:
            break
        try:
            p.popen.wait(timeout=max(0.05, remaining))
        except Exception:
            # Still running
            pass

    # Step 3: force kill any still-running
    for p in procs:
        if p.is_running():
            _kill_process(p)

    # Cleanup temp paths
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return False
        for path in list(info.temp_paths):
            try:
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass
        info.state = RunState.CANCELED
        info.message = f"Canceled: {reason}"
        info.ended_at = _now()
        info.updated_at = _now()

    logger.debug("Run %s canceled (%s)", run_id, reason)
    return True


def complete_run(run_id: str, message: str = "") -> None:
    """Mark a run as completed."""
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return
        info.state = RunState.COMPLETED
        if message:
            info.message = message
        info.ended_at = _now()
        info.updated_at = _now()


def fail_run(run_id: str, error_message: str) -> None:
    """Mark a run as failed."""
    with _registry_lock:
        info = _registry.get(run_id)
        if not info:
            return
        info.state = RunState.ERROR
        info.error = error_message
        info.message = error_message
        info.ended_at = _now()
        info.updated_at = _now()


def remove_run(run_id: str) -> bool:
    """Remove a run from the registry (no process interaction)."""
    with _registry_lock:
        return _registry.pop(run_id, None) is not None
