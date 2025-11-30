"""
Dataset upload & management routes.

Provides:
  - POST /v1/datasets/upload
      * Upload a single unified CSV (long-form) OR a Danim-style wide-form bundle
        (X.csv, Y.csv, R.csv, optional Group_lable.csv) which will be unified
        into a long-form CSV usable by the animation pipeline.
  - GET /v1/datasets
      * List registered datasets for the current runtime (in-memory registry).
  - GET /v1/datasets/{dataset_id}
      * Get metadata for a specific dataset.
  - DELETE /v1/datasets/{dataset_id}
      * Remove dataset files & metadata.

Notes:
  - Datasets are stored under artifacts/datasets. StaticFiles already mounted
    at /static in api.main, so a dataset's relative URL is /static/datasets/<file>.
  - Registry is in-memory; if the server restarts, previously uploaded files
    remain on disk but are not auto-registered. (Could be extended later.)
  - Unified bubble dataset columns: entity,time,x,y,r,group
  - A single uploaded CSV is assumed ready for use; minimal header inspection done.

Future extensions:
  - Persist registry to disk (JSON).
  - Support multi-tenant user scoping via user_id (add field if needed).
  - Add validation routines & SSE streaming for richer diagnostics.

"""

from __future__ import annotations

import csv
import hashlib
import os
import re
import shutil
import time
import uuid
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Depends
from pydantic import BaseModel, Field

from api.persistence.dataset_store import (
    persist_dataset,
    delete_dataset_row,
    list_dataset_rows,
    dataset_exists_by_checksum,
    get_dataset_by_checksum,
    get_dataset_by_id,
)
from api.routes.auth import get_current_user_optional

# Attempt to import the existing Danim ingestion helper (bubble unifier).
try:
    from agents.tools.data_ingestion import unify_danim_files  # type: ignore
except Exception:
    unify_danim_files = None  # type: ignore

DATASETS_SUBDIR = os.path.join("artifacts", "datasets")
os.makedirs(DATASETS_SUBDIR, exist_ok=True)

router = APIRouter(prefix="/datasets", tags=["datasets"])

# In-memory registry
_DATASET_REGISTRY: Dict[str, "DatasetMeta"] = {}
_REGISTRY_LOCK = Lock()


class DatasetMeta(BaseModel):
    dataset_id: str
    created_at: int
    chart_type_hint: Optional[str] = Field(
        None, description="Optional inferred chart type ('bubble', 'distribution', etc.)"
    )
    unified: bool = Field(
        False, description="True if this was created by unifying Danim-style wide-form files"
    )
    original_files: List[str] = Field(
        default_factory=list, description="List of original uploaded filenames (relative paths)"
    )
    unified_path: Optional[str] = Field(
        None, description="Path to the unified CSV (absolute)"
    )
    unified_rel_url: Optional[str] = Field(
        None, description="Relative URL (under /static) to access the unified CSV"
    )
    size_bytes: Optional[int] = None
    columns: List[str] = Field(default_factory=list)
    sha256: Optional[str] = None


class DatasetListResponse(BaseModel):
    datasets: List[DatasetMeta]


class UploadResponse(BaseModel):
    dataset: DatasetMeta


@router.get("", response_model=DatasetListResponse, status_code=status.HTTP_200_OK)
def list_datasets() -> DatasetListResponse:
    with _REGISTRY_LOCK:
        return DatasetListResponse(datasets=list(_DATASET_REGISTRY.values()))


@router.get("/{dataset_id}", response_model=DatasetMeta, status_code=status.HTTP_200_OK)
def get_dataset(dataset_id: str) -> DatasetMeta:
    with _REGISTRY_LOCK:
        if dataset_id not in _DATASET_REGISTRY:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return _DATASET_REGISTRY[dataset_id]


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
def delete_dataset(dataset_id: str, current_user=Depends(get_current_user_optional)) -> Dict[str, str]:
    # Owner check against persisted row (if any)
    persisted = None
    try:
        persisted = get_dataset_by_id(dataset_id)
    except Exception:
        persisted = None
    if persisted and persisted.user_id:
        if not current_user or current_user.id != persisted.user_id:
            raise HTTPException(status_code=403, detail="Not owner of dataset")

    with _REGISTRY_LOCK:
        meta = _DATASET_REGISTRY.get(dataset_id)
        if not meta and not persisted:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Prefer meta from registry for file cleanup; if absent but persisted exists we cannot safely infer file paths.
        if meta:
            # Remove files
            for rel_path in meta.original_files:
                abs_path = os.path.join(os.getcwd(), rel_path) if not os.path.isabs(rel_path) else rel_path
                if os.path.exists(abs_path):
                    try:
                        os.remove(abs_path)
                    except Exception:
                        pass
            if meta.unified_path and os.path.exists(meta.unified_path):
                try:
                    os.remove(meta.unified_path)
                except Exception:
                    pass
            # Remove containing temp dir if empty (best-effort)
            if meta.unified_path:
                _parent = os.path.dirname(meta.unified_path)
                if os.path.isdir(_parent):
                    try:
                        os.rmdir(_parent)
                    except Exception:
                        pass
            if dataset_id in _DATASET_REGISTRY:
                del _DATASET_REGISTRY[dataset_id]

    # Remove DB row (ignore failures)
    try:
        delete_dataset_row(dataset_id)
    except Exception:
        pass

    return {"status": "deleted", "dataset_id": dataset_id}


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset(
    file: Optional[UploadFile] = File(
        default=None,
        description="Single unified CSV (long-form). If provided, Danim-style files are ignored.",
    ),
    x_file: Optional[UploadFile] = File(
        default=None, description="Danim-style X.csv (wide-form) for bubble charts."
    ),
    y_file: Optional[UploadFile] = File(
        default=None, description="Danim-style Y.csv (wide-form) for bubble charts."
    ),
    r_file: Optional[UploadFile] = File(
        default=None, description="Danim-style R.csv (wide-form) for bubble charts."
    ),
    group_file: Optional[UploadFile] = File(
        default=None, description="Optional Danim Group_lable.csv (entity to group mapping)."
    ),
    chart_type_hint: Optional[str] = Query(
        default=None,
        description="Optional explicit chart type hint: 'bubble', 'distribution', etc.",
    ),
    force_unify: bool = Query(
        default=False,
        description="If true, will attempt unification even if a single file is passed (ignored if only file is present).",
    ),
    current_user=Depends(get_current_user_optional),
    skip_duplicate: bool = Query(
        default=True,
        description="If true, will not insert a new DB row when checksum already exists; returns existing dataset metadata.",
    ),
) -> UploadResponse:
    """
    Upload dataset(s) for animation.

    Modes:
      1) Unified CSV (long-form):
         Provide 'file' only. We store it directly.

      2) Danim-style bundle:
         Provide x_file, y_file, r_file (required trio), and optionally group_file.
         These are saved, then unified into a single CSV using available ingestion logic.

    Returns metadata including dataset_id suitable for referencing in future
    /v1/agents/ANIMATION_AGENT/runs requests (e.g., mention csv_path=<unified_rel_url>).
    """
    timestamp = int(time.time())
    created_at = timestamp

    # Determine operation mode
    single_mode = bool(file) and not any([x_file, y_file, r_file, group_file])
    bundle_mode = any([x_file, y_file, r_file])  # Accept partial -> validate below

    if not single_mode and not bundle_mode:
        raise HTTPException(
            status_code=400,
            detail="No files provided. Upload a unified CSV (file) or Danim-style bundle (x_file,y_file,r_file).",
        )

    if single_mode and force_unify:
        # Force unify doesn't apply when only one file is provided; warn but continue.
        pass

    dataset_dir = os.path.join(
        DATASETS_SUBDIR, f"dataset_{datetime.utcfromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')}"
    )
    os.makedirs(dataset_dir, exist_ok=True)

    original_files: List[str] = []
    unified_path: Optional[str] = None
    unified_rel_url: Optional[str] = None
    columns: List[str] = []
    sha256: Optional[str] = None
    unified = False

    if single_mode:
        if not file:
            raise HTTPException(
                status_code=400,
                detail="No file provided for single CSV upload.",
            )
        saved_name = sanitize_filename(file.filename or f"dataset_{timestamp}.csv")
        abs_path = os.path.join(dataset_dir, saved_name)
        content = await file.read()
        with open(abs_path, "wb") as f_out:
            f_out.write(content)
        original_files.append(os.path.relpath(abs_path))
        sha256 = hashlib.sha256(content).hexdigest()
        unified_path = abs_path
        unified_rel_url = rel_url_for(unified_path)
        columns = read_csv_headers(unified_path)

    else:
        # Validate presence of required wide-form files
        if not (x_file and y_file and r_file):
            raise HTTPException(
                status_code=400,
                detail="Danim-style upload requires x_file, y_file, and r_file (R.csv).",
            )
        # Save the bundle
        bundle_map = {
            "X.csv": x_file,
            "Y.csv": y_file,
            "R.csv": r_file,
        }
        if group_file:
            bundle_map["Group_lable.csv"] = group_file

        for target_name, up in bundle_map.items():
            abs_path = os.path.join(dataset_dir, target_name)
            content = await up.read()
            with open(abs_path, "wb") as f_out:
                f_out.write(content)
            original_files.append(os.path.relpath(abs_path))

        # Attempt unification
        output_unified = os.path.join(dataset_dir, "unified.csv")
        try:
            if unify_danim_files is None:
                raise RuntimeError("Ingestion function unify_danim_files not available in this build.")
            ingestion = unify_danim_files(base_dir=dataset_dir, output_path=output_unified)  # type: ignore
            if not os.path.exists(ingestion.unified_path):
                raise RuntimeError("Unification did not produce a unified CSV.")
            unified_path = ingestion.unified_path
            unified_rel_url = rel_url_for(unified_path)
            unified = True
            columns = read_csv_headers(unified_path)
            sha256 = sha256_file(unified_path)
        except Exception as e:
            # On failure, clean up directory (keep original for troubleshooting)
            shutil.rmtree(dataset_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to unify Danim-style bundle: {e}",
            )

    size_bytes = os.path.getsize(unified_path) if unified_path and os.path.exists(unified_path) else None

    # Derive dataset_id from hash or fallback to timestamp
    dataset_id = str(uuid.uuid4())

    meta = DatasetMeta(
        dataset_id=dataset_id,
        created_at=created_at,
        chart_type_hint=normalize_chart_type_hint(chart_type_hint, columns),
        unified=unified,
        original_files=original_files,
        unified_path=unified_path,
        unified_rel_url=unified_rel_url,
        size_bytes=size_bytes,
        columns=columns,
        sha256=sha256,
    )

    # Dedup by checksum if requested and checksum available
    if skip_duplicate and sha256:
        try:
            existing_row = get_dataset_by_checksum(sha256)
            if existing_row and existing_row.storage_path:
                # Rebuild meta pointing to existing dataset (do not re-register new one)
                existing_meta = DatasetMeta(
                    dataset_id=existing_row.dataset_id,
                    created_at=created_at,
                    chart_type_hint=meta.chart_type_hint,
                    unified=unified,
                    original_files=original_files,
                    unified_path=unified_path,
                    unified_rel_url=existing_row.storage_path,
                    size_bytes=existing_row.size_bytes,
                    columns=columns,
                    sha256=sha256,
                )
                with _REGISTRY_LOCK:
                    _DATASET_REGISTRY[existing_row.dataset_id] = existing_meta
                return UploadResponse(dataset=existing_meta)
        except Exception:
            # Ignore checksum lookup errors; proceed as normal
            pass

    with _REGISTRY_LOCK:
        _DATASET_REGISTRY[dataset_id] = meta

    # Persist to DB with authenticated user_id (if any)
    try:
        persist_dataset(meta, user_id=(current_user.id if current_user else None))
    except Exception:
        pass

    return UploadResponse(dataset=meta)


# -----------------------
# Helper Functions
# -----------------------


def sanitize_filename(name: str) -> str:
    base = os.path.basename(name)
    # Strip unsafe characters
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    if not base.lower().endswith(".csv"):
        base += ".csv"
    return base


def read_csv_headers(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            first = next(reader, [])
            return [h.strip() for h in first if h.strip()]
    except Exception:
        return []


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_url_for(abs_path: str) -> str:
    # abs_path like /.../artifacts/datasets/<dir>/unified.csv
    # We expose under /static/datasets/...
    artifacts_root = os.path.abspath("artifacts")
    try:
        rel_inside = os.path.relpath(abs_path, artifacts_root)
    except Exception:
        return ""
    return f"/static/{rel_inside}".replace("\\", "/")


@router.get("/db", status_code=status.HTTP_200_OK)
def list_datasets_db(
    user_only: bool = Query(
        default=False,
        description="If true, returns only datasets owned by the authenticated user.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user_optional),
):
    """
    List datasets from the persisted database table (public.datasets).
    """
    user_id = None
    if user_only:
        user_id = current_user.id if current_user else None
        if user_only and not user_id:
            # No auth supplied
            return {"datasets": []}
    rows = list_dataset_rows(user_id=user_id, limit=limit, offset=offset)
    payload = [
        {
            "dataset_id": r.dataset_id,
            "user_id": r.user_id,
            "filename": r.filename,
            "storage_path": r.storage_path,
            "size_bytes": r.size_bytes,
            "checksum": r.checksum,
            "mime_type": r.mime_type,
        }
        for r in rows
    ]
    return {"datasets": payload}
@router.get("/db/{dataset_id}", status_code=status.HTTP_200_OK)
def get_dataset_db(
    dataset_id: str,
    current_user=Depends(get_current_user_optional),
):
    """
    Fetch a single dataset from the persisted database.
    Enforces ownership if the dataset has a user_id.
    """
    row = get_dataset_by_id(dataset_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if row.user_id:
        if not current_user or current_user.id != row.user_id:
            raise HTTPException(status_code=403, detail="Not owner of dataset")
    return {
        "dataset": {
            "dataset_id": row.dataset_id,
            "user_id": row.user_id,
            "filename": row.filename,
            "storage_path": row.storage_path,
            "size_bytes": row.size_bytes,
            "checksum": row.checksum,
            "mime_type": row.mime_type,
        }
    }
def normalize_chart_type_hint(hint: Optional[str], columns: List[str]) -> Optional[str]:
    # If provided, trust user. Otherwise heuristics:
    if hint:
        return hint
    cols_lower = {c.lower() for c in columns}
    # Bubble heuristic
    if {"x", "y", "r", "time"}.issubset(cols_lower):
        return "bubble"
    # Distribution heuristic
    if {"value", "time"}.issubset(cols_lower):
        return "distribution"
    return None


__all__ = [
    "router",
    "DatasetMeta",
    "DatasetListResponse",
    "UploadResponse",
]
