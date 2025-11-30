"""
Export/Merge tool using ffmpeg.

This module provides helpers to merge multiple MP4 videos into a single MP4
using ffmpeg, compatible with the Agent API SSE pipeline.

Primary entry points:
- export_merge_stream(video_urls, title_slug="exported", user_id="local")
  Yields event dictionaries suitable for SSE:
    {"event": "RunContent", "content": "..."}
    {"event": "RunError", "content": "..."}
    {"event": "RunContent", "content": "Export completed.", "videos": [{"id": 1, "eta": 0, "url": "<public-url>"}]}

- export_merge(video_urls, title_slug="exported", user_id="local")
  Non-streaming helper that returns {"video_url": "<public-url>"} or raises ExportError.

Behavior:
- Downloads remote URLs (http/https) into a temporary working directory.
- Resolves local static URLs (/static/...) into artifact paths without downloading.
- Uses ffmpeg concat filter to merge videos (video only, a=0), outputting a single MP4.
- Writes the final file to artifacts/exports/<unique>.mp4.
- If cloud storage is configured and enabled (use_local_storage == False), uploads to Azure Blob and returns the blob URL.

Notes:
- All inputs must have compatible dimensions/frame rate for the concat filter. If they
  came from the same Manim configuration, they typically are compatible.
- This implementation focuses on video-only concatenation (no audio), which matches
  typical Manim outputs. If your inputs contain audio, you can extend the filter to include a=1.

Requirements:
- ffmpeg must be available in PATH.
- Azure upload requires azure-storage-blob installed and settings configured.

"""

from __future__ import annotations

import os
import uuid
import time
import shutil
import tempfile
import subprocess
from typing import List, Optional, Dict
from urllib.parse import urlparse
from shutil import which

from api.settings import api_settings


class ExportError(Exception):
    """Raised when exporting (merging) videos fails."""


def _ensure_dirs(*paths: str) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


def _artifacts_dir() -> str:
    return os.path.join(os.getcwd(), "artifacts")


def _resolve_static_to_artifacts(static_url: str) -> Optional[str]:
    """
    Convert a /static/... URL into its corresponding artifacts filesystem path.

    Example:
        /static/videos/file.mp4 -> <cwd>/artifacts/videos/file.mp4
    """
    if not static_url.startswith("/static/"):
        return None
    rel = static_url[len("/static/") :]  # e.g., "videos/file.mp4"
    return os.path.join(_artifacts_dir(), rel)


def _download_if_needed(url: str, dest_dir: str) -> str:
    """
    Resolve a given video URL into a local filesystem path:
    - If it's a /static/... URL, convert to artifacts path (no download).
    - If it's a file path (file:// or absolute path), return as is (if exists).
    - If it's http(s), download into dest_dir and return the downloaded file path.

    Raises ExportError if resolution or download fails.
    """
    # Try static mapping
    local_from_static = _resolve_static_to_artifacts(url)
    if local_from_static and os.path.isfile(local_from_static):
        return local_from_static

    parsed = urlparse(url)
    # file:// scheme or absolute path
    if parsed.scheme == "file":
        p = parsed.path
        if not os.path.isfile(p):
            raise ExportError(f"File not found: {p}")
        return p

    if parsed.scheme == "" and os.path.isabs(url):
        if not os.path.isfile(url):
            raise ExportError(f"File not found: {url}")
        return url

    # Remote URL: http(s)
    if parsed.scheme in ("http", "https"):
        try:
            import requests
        except Exception as e:
            raise ExportError(f"requests not available to download remote URL: {e}")

        filename = os.path.basename(parsed.path) or f"video-{uuid.uuid4().hex[:8]}.mp4"
        local_path = os.path.join(dest_dir, filename)
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
        except Exception as e:
            raise ExportError(f"Failed to download {url}: {e}")
        return local_path

    # Unknown scheme
    raise ExportError(f"Unsupported video URL: {url}")


def _unique_export_name(user_id: str, title_slug: str) -> str:
    ts = int(time.time())
    rnd = uuid.uuid4().hex[:6]
    return f"export-{user_id}-{title_slug}-{ts}-{rnd}.mp4"


def _upload_to_azure(file_path: str, blob_name: str) -> Optional[str]:
    """
    Upload final MP4 to Azure Blob Storage and return the public URL.
    Returns None if upload is not configured or fails.
    """
    if not api_settings.azure_storage_connection_string or not api_settings.azure_storage_container_name:
        return None
    try:
        from azure.storage.blob import BlobServiceClient
    except Exception:
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
        account = service_client.account_name
        return f"https://{account}.blob.core.windows.net/{api_settings.azure_storage_container_name}/{blob_name}"
    except Exception:
        return None


def _build_ffmpeg_concat_command(inputs: List[str], out_path: str) -> List[str]:
    """
    Build an ffmpeg command that concatenates N inputs into a single output using filter_complex.
    This version concatenates video streams only (a=0), which is suitable for Manim outputs.

    cmd example:
        ffmpeg -y -i in1.mp4 -i in2.mp4 ... -filter_complex "concat=n=N:v=1:a=0 [v]" -map "[v]" -movflags +faststart out.mp4
    """
    cmd: List[str] = ["ffmpeg", "-y"]
    for p in inputs:
        cmd.extend(["-i", p])

    n = len(inputs)
    filter_expr = f"concat=n={n}:v=1:a=0 [v]"
    cmd.extend(
        [
            "-filter_complex",
            filter_expr,
            "-map",
            "[v]",
            "-movflags",
            "+faststart",
            out_path,
        ]
    )
    return cmd


def export_merge(video_urls: List[str], title_slug: str = "exported", user_id: str = "local") -> Dict[str, str]:
    """
    Non-streaming export/merge function.
    Returns: {"video_url": "<public-url>"}
    Raises ExportError on failure.
    """
    if not video_urls:
        raise ExportError("No videos provided for export/merge.")

    if which("ffmpeg") is None:
        raise ExportError("ffmpeg not found in PATH. Please install ffmpeg in the runtime environment.")

    artifacts = _artifacts_dir()
    exports_dir = os.path.join(artifacts, "exports")
    _ensure_dirs(artifacts, exports_dir)

    # Working directory for downloads and intermediate files
    work_dir = os.path.join(artifacts, "work", f"export-{uuid.uuid4().hex[:8]}")
    _ensure_dirs(work_dir)

    local_inputs: List[str] = []
    try:
        # Resolve all URLs to local files
        for url in video_urls:
            local_path = _download_if_needed(url, work_dir)
            if not os.path.isfile(local_path):
                raise ExportError(f"Input video not found or invalid: {url}")
            local_inputs.append(local_path)

        # Build output path
        out_name = _unique_export_name(user_id=user_id, title_slug=title_slug)
        out_path = os.path.join(exports_dir, out_name)

        # Build concat command and run with timeout
        cmd = _build_ffmpeg_concat_command(local_inputs, out_path)
        try:
            proc = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=api_settings.export_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise ExportError(f"Export/merge timed out after {api_settings.export_timeout_seconds}s")
        except Exception as e:
            raise ExportError(f"Failed running ffmpeg: {e}")

        if proc.returncode != 0:
            # Include a trimmed tail of stderr for debugging
            err_tail = (proc.stderr or "")[-2000:]
            raise ExportError(f"ffmpeg merge failed (exit {proc.returncode}).\n{err_tail}")

        # Determine public URL: local or Azure
        public_url: Optional[str] = None
        if not api_settings.use_local_storage:
            blob_url = _upload_to_azure(out_path, out_name)
            if blob_url:
                public_url = blob_url
        if not public_url:
            public_url = f"/static/exports/{out_name}"

        return {"video_url": public_url}
    finally:
        # Cleanup working dir (downloads)
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def export_merge_stream(
    video_urls: List[str],
    title_slug: str = "exported",
    user_id: str = "local",
) -> "Generator[dict, None, None]":
    """
    Streaming export/merge function that yields event dictionaries suitable for SSE.

    Yields:
      - {"event": "RunContent", "content": "Starting export..."}
      - {"event": "RunContent", "content": f"Downloading inputs ({i}/{n})..."} (per input)
      - {"event": "RunContent", "content": "Merging videos..."}
      - {"event": "RunContent", "content": "Export completed.", "videos": [{"id": 1, "eta": 0, "url": "<public-url>"}]}
      - {"event": "RunError", "content": "<message>"} on failures
    """
    if not video_urls:
        yield {"event": "RunError", "content": "No videos provided for export/merge."}
        return

    if which("ffmpeg") is None:
        yield {"event": "RunError", "content": "ffmpeg not found in PATH. Please install ffmpeg in the runtime environment."}
        return

    yield {"event": "RunContent", "content": "Starting export..."}

    artifacts = _artifacts_dir()
    exports_dir = os.path.join(artifacts, "exports")
    _ensure_dirs(artifacts, exports_dir)

    work_dir = os.path.join(artifacts, "work", f"export-{uuid.uuid4().hex[:8]}")
    _ensure_dirs(work_dir)

    local_inputs: List[str] = []
    try:
        total = len(video_urls)
        for i, url in enumerate(video_urls, start=1):
            yield {"event": "RunContent", "content": f"Resolving input ({i}/{total})..."}
            try:
                local_path = _download_if_needed(url, work_dir)
            except ExportError as e:
                yield {"event": "RunError", "content": str(e)}
                return
            if not os.path.isfile(local_path):
                yield {"event": "RunError", "content": f"Input not found after resolve: {url}"}
                return
            local_inputs.append(local_path)

        out_name = _unique_export_name(user_id=user_id, title_slug=title_slug)
        out_path = os.path.join(exports_dir, out_name)

        yield {"event": "RunContent", "content": "Merging videos..."}
        cmd = _build_ffmpeg_concat_command(local_inputs, out_path)
        try:
            proc = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=api_settings.export_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            yield {"event": "RunError", "content": f"Export/merge timed out after {api_settings.export_timeout_seconds}s"}
            return
        except Exception as e:
            yield {"event": "RunError", "content": f"Failed running ffmpeg: {e}"}
            return

        if proc.returncode != 0:
            err_tail = (proc.stderr or "")[-2000:]
            yield {"event": "RunError", "content": f"ffmpeg merge failed (exit {proc.returncode}).\n{err_tail}"}
            return

        # Decide final URL
        public_url: Optional[str] = None
        if not api_settings.use_local_storage:
            blob_url = _upload_to_azure(out_path, out_name)
            if blob_url:
                public_url = blob_url
        if not public_url:
            public_url = f"/static/exports/{out_name}"

        yield {
            "event": "RunContent",
            "content": "Export completed.",
            "videos": [{"id": 1, "eta": 0, "url": public_url}],
        }
    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
