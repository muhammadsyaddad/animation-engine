"""
Preview tool to render PNG frames using Manim and return image URLs served via FastAPI StaticFiles.

Features:
- Two entry points:
  * generate_manim_preview: one-shot render then sample frames.
  * generate_manim_preview_stream: threaded render with heartbeat & progress events.
- Preset system (preview vs final) controlling frame_rate and sampling defaults.
- Optional override of frame rate via preview_frame_rate argument.
- Early-exit logic for preview mode: limits number of animation actions (Scene.play calls)
  to accelerate large scenes without requiring changes to generated user code.

Early Exit Strategy (preview preset):
- Override Scene.play so after PREVIEW_LIMIT_ACTIONS plays, subsequent plays are skipped.
- Override Scene.wait to skip waits after early-exit is triggered.
- Override Scene.add / add_foreground_mobject to reduce overhead post early-exit.
Environment variable:
  PREVIEW_LIMIT_ACTIONS (default "8")
"""

from __future__ import annotations

import os
import re
import uuid
import shutil
import subprocess
import time
import logging
from typing import List, Tuple, Optional, Generator
from shutil import which

# Setup module logger
logger = logging.getLogger("animation_pipeline.preview_manim")
try:
    from api.run_registry import register_temp_path, start_tracked_process, get_run, RunState
except Exception:
    register_temp_path = None  # type: ignore
    start_tracked_process = None  # type: ignore
    get_run = None  # type: ignore
    RunState = None  # type: ignore


class PreviewError(Exception):
    """Raised when Manim preview generation fails."""


# ---- Preview Error Classification & Constants ----
PREVIEW_HEARTBEAT_INTERVAL_SECONDS = 5  # configurable later via settings
MAX_CLASSIFICATION_MESSAGE_LEN = 500


def classify_preview_error(err: str) -> tuple[str, str, bool]:
    """
    Classify a preview error string into (category, message, allow_llm_fix).
    """
    e = (err or "").lower()
    if "nonetype" in e and ".find" in e and "text(" in e:
        return ("MissingAxisLabel",
                "Axis label constant was None. Supply X_LABEL/Y_LABEL or remove axis label code.",
                False)
    if "keyerror" in e and ("column" in e or "[" in e):
        return ("MissingDataColumn",
                "Scene code references a missing dataset column. Verify melted dataset headers and data binding.",
                False)
    if ("could not convert" in e) or ("nan" in e and "value" in e):
        return ("DataTypeIssue",
                "Non-numeric / NaN data encountered. Clean or coerce values before rendering.",
                False)
    if "modulenotfounderror" in e or "importerror" in e:
        return ("EnvironmentDependency",
                "Missing Python dependency for template. Ensure required libraries are installed.",
                False)
    if "memoryerror" in e or ("killed" in e and "process" in e):
        return ("ResourceLimit",
                "Render exceeded resource limits. Sample fewer groups/time points or reduce frame count.",
                False)
    if "syntaxerror" in e or "nameerror" in e:
        return ("SceneSyntax",
                "Scene code has a syntax/name issue. Attempting automated fix.",
                True)
    if "timed out" in e and "preview" in e:
        return ("PerformanceTimeout",
                "Preview timed out. Reduce dataset size (sampling) or increase preview_timeout_seconds.",
                False)
    return ("UnknownRuntime",
            "Preview failed with an unknown error. Attempting limited fix.",
            True)


def _get_preview_frame_config(aspect_ratio: str) -> Tuple[Tuple[int, int], float]:
    """
    Base resolution & width for preview. (Preview uses smaller sizes than full render.)
    """
    if aspect_ratio == "16:9":
        return (1280, 720), 10.0
    if aspect_ratio == "9:16":
        return (720, 1280), 6.0
    if aspect_ratio == "1:1":
        return (720, 720), 6.0
    return (1280, 720), 10.0


def _get_preview_preset(aspect_ratio: str, preset: str) -> Tuple[Tuple[int, int], float, int, int, int]:
    """
    Return (frame_size, frame_width, frame_rate, default_sample_every, default_max_frames)
    for the given preset.
    Presets:
      - preview: lower fps, aggressive sampling.
      - final: higher fps, minimal sampling.
    """
    frame_size, frame_width = _get_preview_frame_config(aspect_ratio)
    preset_norm = (preset or "preview").lower()
    if preset_norm == "final":
        frame_rate = 24
        default_sample_every = 1
        default_max_frames = 300
    else:
        frame_rate = 10
        default_sample_every = 4
        default_max_frames = 50
    return frame_size, frame_width, frame_rate, default_sample_every, default_max_frames


def _ensure_dirs(*paths: str) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


def _list_pngs(root_dir: str) -> List[str]:
    pngs: List[str] = []
    for r, _dirs, files in os.walk(root_dir):
        for fn in files:
            if fn.lower().endswith(".png"):
                pngs.append(os.path.join(r, fn))
    return pngs


_NUM_RE = re.compile(r"(\d+)(?!.*\d)")


def _extract_frame_index(path: str) -> int:
    base = os.path.basename(path)
    m = _NUM_RE.search(base)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except Exception:
        return 0


def _sample_frames(paths: List[str], sample_every: int, max_frames: int) -> List[str]:
    if not paths:
        return []
    sorted_paths = sorted(paths, key=_extract_frame_index)
    if sample_every <= 1:
        sampled = sorted_paths[:max_frames]
    else:
        sampled = [p for p in sorted_paths if _extract_frame_index(p) % sample_every == 0]
        if not sampled:
            sampled = sorted_paths[::sample_every]
        sampled = sampled[:max_frames]
    return sampled


def generate_manim_preview(
    code: str,
    class_name: str = "GenScene",
    *,
    aspect_ratio: str = "16:9",
    sample_every: int = 4,
    max_frames: int = 50,
    user_id: str = "local",
    project_name: str = "project",
    iteration: int = 1,
    run_id: Optional[str] = None,
    quality: str = "low",
    preset: str = "preview",
    preview_frame_rate: Optional[int] = None,
    enable_early_exit: bool = True,
) -> dict:
    """
    Render preview frames and return image metadata.

    Args:
        code: Manim Python code defining the scene class.
        class_name: Scene class name to render.
        aspect_ratio: "16:9" | "9:16" | "1:1".
        sample_every: Keep 1 of every N frames (post-render sampling).
        max_frames: Cap returned frames.
        user_id/project_name/iteration: components for uniqueness in token.
        run_id: Optional run identifier for registry tracking.
        quality: "low" | "medium" | "high" (maps to manim -q flags).
        preset: "preview" or "final".
        preview_frame_rate: Optional explicit frame_rate override (otherwise preset default).
        enable_early_exit: Toggle early-exit logic in preview mode.

    Returns:
        {
            "images": [{"url": "...", "revised_prompt": ""}, ...],
            "preview_token": "<token>",
            "count": <int>
        }
    """
    logger.info(f"[PREVIEW] ========== PREVIEW GENERATION STARTED ==========")
    logger.info(f"[PREVIEW] Parameters | run_id={run_id} | aspect_ratio={aspect_ratio} | quality={quality} | preset={preset}")
    logger.info(f"[PREVIEW] Sampling config | sample_every={sample_every} | max_frames={max_frames}")
    logger.debug(f"[PREVIEW] Code length: {len(code)} characters")

    if which("manim") is None:
        logger.error("[PREVIEW] Manim CLI not found in PATH")
        raise PreviewError("Manim CLI not found in PATH. Ensure manim is installed and available.")

    artifacts_dir = os.path.join(os.getcwd(), "artifacts")
    previews_dir = os.path.join(artifacts_dir, "previews")
    work_dir = os.path.join(artifacts_dir, "work", str(uuid.uuid4()))
    _ensure_dirs(artifacts_dir, previews_dir, work_dir)
    if run_id and register_temp_path:
        register_temp_path(run_id, work_dir)

    frame_size, frame_width, preset_frame_rate, preset_sample_every, preset_max_frames = _get_preview_preset(
        aspect_ratio, preset
    )
    logger.debug(f"[PREVIEW] Preset config | frame_size={frame_size} | frame_width={frame_width} | preset_frame_rate={preset_frame_rate}")

    # If caller used default function values AND preset is final, apply final defaults.
    if preset.lower() == "final":
        if sample_every == 4:  # function default
            sample_every = preset_sample_every
        if max_frames == 50:   # function default
            max_frames = preset_max_frames

    effective_frame_rate = preview_frame_rate if preview_frame_rate is not None else preset_frame_rate
    logger.info(f"[PREVIEW] Effective settings | frame_rate={effective_frame_rate} | sample_every={sample_every} | max_frames={max_frames}")

    early_exit_block = ""
    if enable_early_exit and preset.lower() == "preview":
        # Overriding Scene.play / wait / add to reduce work after limit reached.
        early_exit_block = r"""
# ---- Early Exit (Preview Mode) ----
import os as _os
from manim.scene.scene import Scene as _Scene
_PREVIEW_LIMIT_ACTIONS = int(_os.environ.get("PREVIEW_LIMIT_ACTIONS", "8"))
_play_action_counter = 0
_exit_preview_now = False

_original_play = _Scene.play
_original_wait = _Scene.wait
_original_add = _Scene.add
_original_add_fg = _Scene.add_foreground_mobject

def _preview_play(self, *args, **kwargs):
    global _play_action_counter, _exit_preview_now
    if _exit_preview_now:
        return  # skip further animations
    _play_action_counter += 1
    if _play_action_counter >= _PREVIEW_LIMIT_ACTIONS:
        _exit_preview_now = True
        # Execute this final animation once, then future ones skipped
        return _original_play(self, *args, **kwargs)
    return _original_play(self, *args, **kwargs)

def _preview_wait(self, duration=0.0):
    if _exit_preview_now:
        return  # skip waits entirely
    return _original_wait(self, duration)

def _preview_add(self, *mobs):
    if _exit_preview_now:
        # Allow minimal additions to keep scene valid; or skip entirely
        return
    return _original_add(self, *mobs)

def _preview_add_fg(self, *mobs):
    if _exit_preview_now:
        return
    return _original_add_fg(self, *mobs)

_Scene.play = _preview_play
_Scene.wait = _preview_wait
_Scene.add = _preview_add
_Scene.add_foreground_mobject = _preview_add_fg
"""

    # Build injected module code.
    mod_code = f"""
from manim import *
from math import *
import os

config.frame_size = {frame_size}
config.frame_width = {frame_width}
config.frame_rate = {effective_frame_rate}

{early_exit_block}

{code}
""".lstrip()

    # Write temporary scene file
    scene_file_name = f"scene_{uuid.uuid4().hex[:6]}.py"
    scene_file_path = os.path.join(work_dir, scene_file_name)
    logger.debug(f"[PREVIEW] Writing scene file: {scene_file_path}")
    with open(scene_file_path, "w", encoding="utf-8") as f:
        f.write(mod_code)

    token = f"preview-{user_id}-{project_name}-{iteration}-{uuid.uuid4().hex[:6]}"
    out_dir = os.path.join(previews_dir, token)
    _ensure_dirs(out_dir)
    logger.info(f"[PREVIEW] Output token: {token} | output_dir: {out_dir}")

    quality_flag = {"low": "-ql", "medium": "-qm", "high": "-qh"}.get(quality.lower(), "-ql")
    cmd = [
        "manim",
        scene_file_path,
        class_name,
        "--format=png",
        quality_flag,
        "--media_dir",
        work_dir,
        "--custom_folders",
        "--disable_caching",
    ]
    logger.info(f"[PREVIEW] Executing Manim command: {' '.join(cmd)}")

    stdout_data = ""
    stderr_data = ""
    try:
        if run_id and start_tracked_process:
            proc = start_tracked_process(
                run_id=run_id,
                cmd=cmd,
                role="preview",
                cwd=work_dir,
                text=True,
                bufsize=1,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            proc = subprocess.Popen(
                cmd,
                cwd=work_dir,
                text=True,
                bufsize=1,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        # Timeout handling via api_settings.preview_timeout_seconds (if provided)
        from api.settings import api_settings  # local import to avoid circulars
        deadline_seconds = float(api_settings.preview_timeout_seconds or 0) or 300.0
        deadline = time.time() + deadline_seconds

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                try: proc.terminate()
                except Exception: pass
                try: proc.kill()
                except Exception: pass
                raise PreviewError(f"Manim preview timed out after {deadline_seconds}s")

            # Cancellation check
            if run_id and get_run and RunState:
                try:
                    info = get_run(run_id)
                    if info and getattr(info, "state", None) == RunState.CANCELED:
                        try: proc.terminate()
                        except Exception: pass
                        try: proc.kill()
                        except Exception: pass
                        raise PreviewError("Preview canceled by user.")
                except Exception:
                    pass

            try:
                out, err = proc.communicate(timeout=min(0.5, max(0.1, remaining)))
                if out:
                    stdout_data += out if isinstance(out, str) else out.decode("utf-8", errors="ignore")
                if err:
                    stderr_data += err if isinstance(err, str) else err.decode("utf-8", errors="ignore")
                break
            except subprocess.TimeoutExpired as e:
                # Accumulate partial output on timeout intervals
                try:
                    if getattr(e, "output", None):
                        part = e.output
                        stdout_data += part if isinstance(part, str) else part.decode("utf-8", errors="ignore")
                except Exception:
                    pass
                try:
                    if getattr(e, "stderr", None):
                        part = e.stderr
                        stderr_data += part if isinstance(part, str) else part.decode("utf-8", errors="ignore")
                except Exception:
                    pass
                continue
    except FileNotFoundError as e:
        raise PreviewError(f"Failed to run manim: {e}")
    except Exception as e:
        raise PreviewError(f"Unexpected error running manim: {e}")

    if proc.returncode != 0:
        tail = (stderr_data or "")[-2000:]
        raise PreviewError(f"Manim preview failed (exit {proc.returncode}).\n{tail}")

    pngs = _list_pngs(work_dir)
    if not pngs:
        pngs = _list_pngs(os.getcwd())
    if not pngs:
        raise PreviewError("No preview frames were generated by Manim.")

    sampled = _sample_frames(pngs, sample_every=sample_every, max_frames=max_frames)

    images: List[dict] = []
    for src in sampled:
        base = os.path.basename(src)
        dst = os.path.join(out_dir, base)
        try:
            shutil.move(src, dst)
        except Exception:
            shutil.copy2(src, dst)
            try: os.remove(src)
            except Exception: pass
        public_url = f"/static/previews/{token}/{base}"
        images.append({"url": public_url, "revised_prompt": ""})

    try:
        shutil.rmtree(work_dir, ignore_errors=True)
    except Exception:
        pass

    return {
        "images": images,
        "preview_token": token,
        "count": len(images),
    }


def generate_manim_preview_stream(
    code: str,
    class_name: str = "GenScene",
    *,
    aspect_ratio: str = "16:9",
    sample_every: int = 4,
    max_frames: int = 50,
    user_id: str = "local",
    project_name: str = "project",
    iteration: int = 1,
    run_id: Optional[str] = None,
    quality: str = "low",
    heartbeat_interval: int = PREVIEW_HEARTBEAT_INTERVAL_SECONDS,
    enable_progress: bool = True,
    preset: str = "preview",
    preview_frame_rate: Optional[int] = None,
    enable_early_exit: bool = True,
) -> Generator[dict, None, None]:
    """
    Streaming variant: yields dict events:
      - RunContent (status / progress / final)
      - RunHeartbeat (elapsed_seconds)
      - RunError (classified error)
    """
    start_time = time.time()
    yield {"event": "RunContent", "content": "Generating preview..."}

    import threading
    result_container: dict = {"result": None, "error": None}

    def _run():
        try:
            result_container["result"] = generate_manim_preview(
                code=code,
                class_name=class_name,
                aspect_ratio=aspect_ratio,
                sample_every=sample_every,
                max_frames=max_frames,
                user_id=user_id,
                project_name=project_name,
                iteration=iteration,
                run_id=run_id,
                quality=quality,
                preset=preset,
                preview_frame_rate=preview_frame_rate,
                enable_early_exit=enable_early_exit,
            )
        except Exception as ex:
            result_container["error"] = ex

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    last_heartbeat = 0.0
    while t.is_alive():
        now = time.time()
        elapsed = int(now - start_time)
        if now - last_heartbeat >= heartbeat_interval:
            heartbeat_payload = {
                "event": "RunHeartbeat",
                "content": "",
                "elapsed_seconds": elapsed,
            }
            if run_id:
                heartbeat_payload["run_id"] = run_id
            yield heartbeat_payload
            last_heartbeat = now

            if enable_progress:
                # Naive total PNG count under artifacts/work and artifacts/previews
                try:
                    artifacts_dir = os.path.join(os.getcwd(), "artifacts")
                    png_count = 0
                    for root in (os.path.join(artifacts_dir, "work"),
                                 os.path.join(artifacts_dir, "previews")):
                        for r, _dirs, files in os.walk(root):
                            for fn in files:
                                if fn.lower().endswith(".png"):
                                    png_count += 1
                    progress_payload = {
                        "event": "RunContent",
                        "content": f"Preview progress: {png_count} frame(s) written...",
                    }
                    if run_id:
                        progress_payload["run_id"] = run_id
                    yield progress_payload
                except Exception:
                    pass
        time.sleep(0.25)

    t.join()

    err = result_container["error"]
    if err:
        if isinstance(err, PreviewError):
            category, msg, allow_fix = classify_preview_error(str(err))
            yield {
                "event": "RunError",
                "content": f"[{category}] {msg}"[:MAX_CLASSIFICATION_MESSAGE_LEN],
                "allow_llm_fix": allow_fix,
            }
        else:
            category, msg, allow_fix = classify_preview_error(str(err))
            yield {
                "event": "RunError",
                "content": f"[{category}] {msg}"[:MAX_CLASSIFICATION_MESSAGE_LEN],
                "allow_llm_fix": allow_fix,
            }
        return

    result = result_container["result"] or {}
    yield {
        "event": "RunContent",
        "content": "Preview generated.",
        "images": result.get("images", []),
        "elapsed_seconds": int(time.time() - start_time),
    }
