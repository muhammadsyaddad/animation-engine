import os
import re
import json
import uuid
import shutil
import subprocess
import time
import select
import logging
from typing import Generator, Tuple, Optional
from shutil import which
from api.settings import api_settings

# Setup module logger
logger = logging.getLogger("animation_pipeline.video_manim")
try:
    from api.run_registry import register_temp_path, register_artifact, start_tracked_process
except Exception:
    register_temp_path = None  # type: ignore
    register_artifact = None  # type: ignore
    start_tracked_process = None  # type: ignore


def _get_frame_config(aspect_ratio: str) -> Tuple[Tuple[int, int], float]:
    """
    Map aspect ratios to frame_size and frame_width used by Manim.

    Returns:
        (frame_size, frame_width)
        - frame_size: (width, height)
        - frame_width: logical width in manim units
    """
    if aspect_ratio == "16:9":
        # 1080p base for faster renders
        return (1920, 1080), 14.22
    if aspect_ratio == "9:16":
        return (1080, 1920), 8.0
    if aspect_ratio == "1:1":
        return (1080, 1080), 8.0
    # Default
    return (1920, 1080), 14.22


def _ensure_dirs(*paths: str) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


def _find_rendered_mp4(root_dir: str, preferred_name: Optional[str] = None) -> Optional[str]:
    """
    Search for the rendered mp4 within a directory tree.

    Args:
        root_dir: The directory to search within.
        preferred_name: If provided, prefer a file that exactly matches this name.

    Returns:
        Absolute path to the first matching mp4 (preferring preferred_name), or None.
    """
    preferred_path = None
    fallback_path = None
    for r, _dirs, files in os.walk(root_dir):
        for fn in files:
            if not fn.lower().endswith(".mp4"):
                continue
            full = os.path.join(r, fn)
            if preferred_name and fn == preferred_name:
                preferred_path = full
                break
            if fallback_path is None:
                fallback_path = full
        if preferred_path:
            break
    return preferred_path or fallback_path

def _upload_to_azure(file_path: str, blob_name: str) -> Optional[str]:
    """
    Upload a file to Azure Blob Storage using settings from api_settings.
    Returns the public blob URL on success, or None if upload not configured.
    """
    if not api_settings.azure_storage_connection_string or not api_settings.azure_storage_container_name:
        return None
    try:
        from azure.storage.blob import BlobServiceClient
    except Exception:
        # Azure SDK not installed
        return None

    try:
        service_client = BlobServiceClient.from_connection_string(
            api_settings.azure_storage_connection_string
        )
        blob_client = service_client.get_blob_client(
            container=api_settings.azure_storage_container_name,
            blob=blob_name,
        )
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        # Construct URL
        account = service_client.account_name
        return f"https://{account}.blob.core.windows.net/{api_settings.azure_storage_container_name}/{blob_name}"
    except Exception:
        return None


def render_manim_stream(
    code: str,
    file_class: str = "GenScene",
    aspect_ratio: str = "16:9",
    project_name: str = "project",
    user_id: str = "local",
    iteration: int = 1,
    run_id: Optional[str] = None,
    quality: str = "low",
) -> Generator[dict, None, None]:
    """
    Render a Manim scene to MP4 and stream progress/results as event dicts.

    Yielded event structure suggestions (consumer can adapt as needed):
        - {"event": "RunContent", "content": "<text status>"}
        - {"event": "RunError", "content": "<error message>"}
        - {"event": "RunContent", "content": "Render completed.", "videos": [{"id": 1, "eta": 0, "url": "/static/videos/xxx.mp4"}]}

    Args:
        code: Full python code containing the class `file_class`.
        file_class: The Scene class to render (e.g., "GenScene").
        aspect_ratio: One of "16:9", "9:16", "1:1". Defaults to "16:9".
        project_name: A name slug to include in the output file naming.
        user_id: Identifier for the current user (for naming/scoping).
        iteration: Iteration number for uniqueness in output naming.

    Notes:
        - Requires `manim` CLI available in PATH.
        - Uses `artifacts/` as base for outputs and temporary work.
        - Designed for low-latency feedback: parses stderr for progress like "Animation N: X%".
    """
    logger.info(f"[RENDER] ========== VIDEO RENDER STARTED ==========")
    logger.info(f"[RENDER] Parameters | run_id={run_id} | aspect_ratio={aspect_ratio} | quality={quality}")
    logger.info(f"[RENDER] User context | user_id={user_id} | project_name={project_name} | iteration={iteration}")
    logger.debug(f"[RENDER] Code length: {len(code)} characters")

    # Quick check for manim CLI
    if which("manim") is None:
        logger.error("[RENDER] Manim CLI not found in PATH")
        yield {
            "event": "RunError",
            "content": "Manim CLI not found in PATH. Ensure manim is installed and available."
        }
        return

    artifacts_dir = os.path.join(os.getcwd(), "artifacts")
    videos_dir = os.path.join(artifacts_dir, "videos")
    work_dir = os.path.join(artifacts_dir, "work", str(uuid.uuid4()))

    logger.debug(f"[RENDER] Directories | artifacts={artifacts_dir} | videos={videos_dir} | work={work_dir}")

    _ensure_dirs(artifacts_dir, videos_dir, work_dir)
    if run_id and register_temp_path:
        register_temp_path(run_id, work_dir)
        logger.debug(f"[RENDER] Registered temp path for run_id={run_id}")

    # Prepend config for frame settings to the provided code
    frame_size, frame_width = _get_frame_config(aspect_ratio)
    logger.info(f"[RENDER] Frame config | frame_size={frame_size} | frame_width={frame_width}")
    mod_code = f"""
from manim import *
from math import *
config.frame_size = {frame_size}
config.frame_width = {frame_width}

{code}
""".lstrip()

    # Create a temporary scene file inside the work directory
    scene_file_name = f"scene_{uuid.uuid4().hex[:6]}.py"
    scene_file_path = os.path.join(work_dir, scene_file_name)
    with open(scene_file_path, "w", encoding="utf-8") as f:
        f.write(mod_code)

    # Prepare output naming
    out_stem = f"video-{user_id}-{project_name}-{iteration}-{uuid.uuid4().hex[:6]}"
    out_mp4_name = f"{out_stem}.mp4"

    # Build manim command
    # - Using low quality (-ql) to speed up
    # - custom media dir to the work_dir
    # - force output file name
    quality_flag = {"low": "-ql", "medium": "-qm", "high": "-qh"}.get(quality.lower(), "-ql")
    cmd = [
        "manim",
        scene_file_path,
        file_class,
        "--format=mp4",
        quality_flag,
        "--media_dir", work_dir,
        "--custom_folders",
        "--output_file", out_stem,
        "--disable_caching",
    ]

    # Emit initial status
    yield {"event": "RunContent", "content": "Starting Manim render..."}

    proc: Optional[subprocess.Popen] = None
    current_animation = -1
    current_percentage = -1

    try:
        if run_id and start_tracked_process:
            proc = start_tracked_process(
                run_id=run_id,
                cmd=cmd,
                role="render",
                cwd=work_dir,
                text=True,
                bufsize=1,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                text=True,
                bufsize=1,
            )
        # Start wall-clock timer for timeout handling
        start_time = time.time()
        last_output_time = start_time
        last_heartbeat_time = start_time

        # Non-blocking stream progress parsing using select
        stdout_fd = proc.stdout.fileno() if proc.stdout else None
        stderr_fd = proc.stderr.fileno() if proc.stderr else None
        poll_fds = [fd for fd in (stdout_fd, stderr_fd) if fd is not None]
        QUIET_WATCHDOG_SECONDS = 10  # emit heartbeat if no output for this duration

        while True:
            # Enforce overall render timeout
            if api_settings.render_timeout_seconds and (time.time() - start_time) > api_settings.render_timeout_seconds:
                try: proc.terminate()
                except Exception: pass
                try: proc.kill()
                except Exception: pass
                yield {
                    "event": "RunError",
                    "content": f"Manim render timed out after {api_settings.render_timeout_seconds}s"
                }
                return

            had_line = False
            try:
                ready, _, _ = select.select(poll_fds, [], [], 0.5)
            except Exception:
                ready = []

            # Drain stderr first (progress information)
            if stderr_fd is not None and stderr_fd in ready and proc.stderr:
                line = proc.stderr.readline()
                if line:
                    had_line = True
                    last_output_time = time.time()
                    anim_match = re.search(r"Animation\s+(\d+):", line)
                    if anim_match:
                        new_anim = int(anim_match.group(1))
                        if new_anim != current_animation:
                            current_animation = new_anim
                            current_percentage = -1
                            yield {"event": "RunContent", "content": f"Animation {current_animation}: 0%"}
                    pct_match = re.search(r"(\d+)%", line)
                    if pct_match:
                        new_pct = int(pct_match.group(1))
                        if new_pct != current_percentage:
                            current_percentage = new_pct
                            yield {"event": "RunContent", "content": f"Animation {current_animation}: {current_percentage}%"}

            # Drain stdout (optional informational)
            if stdout_fd is not None and stdout_fd in ready and proc.stdout:
                line = proc.stdout.readline()
                if line:
                    had_line = True
                    last_output_time = time.time()
                    # (stdout lines suppressed)

            now = time.time()
            # Heartbeat / quiet watchdog
            if not had_line and proc.poll() is None:
                if (now - last_output_time) > QUIET_WATCHDOG_SECONDS and (now - last_heartbeat_time) > 2.0:
                    hb_text = "Rendering..."
                    if current_animation >= 0 and current_percentage >= 0:
                        hb_text = f"Animation {current_animation}: {current_percentage}% (working)"
                    yield {"event": "RunContent", "content": hb_text}
                    last_heartbeat_time = now

            # Exit when process finished
            if proc.poll() is not None:
                break

            # Forward informative stdout as needed (not strictly necessary)
            # Removed undefined stdout_line handling; stdout is already drained above.

            # Removed legacy stderr_line handler; progress is handled above via 'line' from proc.stderr.

            # Removed stray duplicate heartbeat block (previous heartbeat logic retained above)
            # Exit loop when process finished and no more output
            # Enforce render timeout (terminate long-running renders)
            if api_settings.render_timeout_seconds and (time.time() - start_time) > api_settings.render_timeout_seconds:
                try:
                    proc.terminate()
                except Exception:
                    pass
                try:
                    proc.kill()
                except Exception:
                    pass
                yield {
                    "event": "RunError",
                    "content": f"Manim render timed out after {api_settings.render_timeout_seconds}s"
                }
                return

            # Removed undefined stdout_line/stderr_line exit check; we already break when proc finishes.

        # Check result
        if proc.returncode != 0:
            # Try to capture the last stderr to show a concise error
            err_tail = ""
            try:
                if proc.stderr:
                    err_tail = proc.stderr.read() or ""
            except Exception:
                pass

            msg = f"Manim render failed (exit {proc.returncode})."
            if err_tail:
                # Shorten very long error logs
                trimmed = err_tail[-2000:]
                msg = f"{msg}\n{trimmed}"

            yield {"event": "RunError", "content": msg}
            return

        # Find the generated mp4 within work_dir
        mp4_path = _find_rendered_mp4(work_dir, preferred_name=out_mp4_name)
        if not mp4_path or not os.path.exists(mp4_path):
            yield {"event": "RunError", "content": "Rendered video file not found."}
            return

        # Move to artifacts/videos with final name
        final_path = os.path.join(videos_dir, out_mp4_name)
        try:
            shutil.move(mp4_path, final_path)
        except Exception:
            # If move fails (maybe across filesystem), try copy then remove
            shutil.copy2(mp4_path, final_path)
            try:
                os.remove(mp4_path)
            except Exception:
                pass

        if run_id and register_artifact:
            register_artifact(run_id, final_path)
        # Construct public URL (served by FastAPI StaticFiles)
        # Determine public URL: upload to Azure if configured and not using local storage
        video_url = None
        if not api_settings.use_local_storage:
            blob_url = _upload_to_azure(final_path, out_mp4_name)
            if blob_url:
                video_url = blob_url
        if not video_url:
            video_url = f"/static/videos/{out_mp4_name}"

        # Emit final event with video info
        yield {
            "event": "RunContent",
            "content": "Render completed.",
            "videos": [
                {"id": 1, "eta": 0, "url": video_url}
            ],
        }

    except FileNotFoundError as e:
        yield {"event": "RunError", "content": f"Command failed: {e}"}
    except Exception as e:
        yield {"event": "RunError", "content": f"Unexpected error: {str(e)}"}
    finally:
        # Cleanup work directory
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            # Ignore cleanup errors
            pass
