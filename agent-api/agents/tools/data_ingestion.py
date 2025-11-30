"""
Multi-file Danim-style dataset ingestion and unified CSV creation.

This module ingests the classic Danim bubble chart dataset layout:
    X.csv      (e.g., life expectancy wide-form)
    Y.csv      (e.g., fertility wide-form)
    R.csv      (e.g., population / radius proxy wide-form)
    Group_lable.csv (optional, maps Entity -> Group)

Typical wide-form structure (header example):
    Entity,1960,1961,1962,1963,...
Each subsequent column is a time token (year or period). Rows are entities.

Goal:
    Produce a single long-form unified CSV with columns:
        entity,time,x,y,r,group
    suitable for the Bubble template generator (generate_bubble_code).

Heuristics & Features:
- Supports both wide-form (Entity + time columns) and already unified long-form
  (entity,time,x,y,r[,group]) — detects and passthrough if already unified.
- Handles missing values gracefully (skips rows missing any of x,y,r).
- Intersects time keys across X/Y/R sets to ensure alignment.
- If a group file is provided, merges group labels; otherwise assigns "ALL".
- Attempts multiple common entity column name variants.
- Pure standard library (csv + typing + dataclasses); no external dependencies.

Main entry:
    unify_danim_files(
        base_dir: str,
        x_file: str = "X.csv",
        y_file: str = "Y.csv",
        r_file: str = "R.csv",
        group_file: str = "Group_lable.csv",
        output_path: Optional[str] = None,
        entity_col_candidates: Sequence[str] = ("Entity","Country","Name","Label","entity","country","name","label","ID","id"),
    ) -> IngestionResult

Dataclass:
    IngestionResult:
        unified_path: str
        rows_count: int
        entities_count: int
        times_count: int
        columns: List[str]
        warnings: List[str]
        metadata: Dict[str, Any]

Example:
    from agents.tools.data_ingestion import unify_danim_files
    result = unify_danim_files("Danim/DATA", output_path="artifacts/datasets/unified.csv")
    print(result.unified_path, result.rows_count)

"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Any, Tuple, Set


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IngestionResult:
    unified_path: str
    rows_count: int
    entities_count: int
    times_count: int
    columns: List[str]
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _safe_read_csv(path: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Read a CSV file into a list of row dicts and return (rows, headers).
    Raises FileNotFoundError if path missing.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows: List[Dict[str, str]] = [dict(r) for r in reader]
    return rows, headers


def _detect_entity_column(headers: List[str], candidates: Sequence[str]) -> Optional[str]:
    lower = {h.lower(): h for h in headers}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def _is_unified_format(headers: List[str]) -> bool:
    """
    Detect if a file is already in unified long-form format:
    Must contain at least: entity, time and (x|y|r) columns.
    """
    required = {"entity", "time"}
    has_required = required.issubset({h.lower() for h in headers})
    has_any_value = any(h.lower() in ("x", "y", "r") for h in headers)
    return has_required and has_any_value


def _parse_wide(rows: List[Dict[str, str]], entity_col: str) -> Tuple[Dict[str, Dict[str, float]], Set[str]]:
    """
    Parse a wide-form file into:
        data[entity][time] = value
    Returns (data_map, time_tokens_set)
    """
    if not rows:
        return {}, set()

    # Time columns are all headers except entity_col
    time_cols = [h for h in rows[0].keys() if h != entity_col]

    data_map: Dict[str, Dict[str, float]] = {}
    time_tokens: Set[str] = set()

    for row in rows:
        entity = (row.get(entity_col) or "").strip()
        if not entity:
            continue
        data_map.setdefault(entity, {})
        for tcol in time_cols:
            raw_val = (row.get(tcol) or "").strip()
            if not raw_val:
                continue
            # Parse float if possible
            try:
                val = float(raw_val)
            except ValueError:
                continue
            data_map[entity][tcol] = val
            time_tokens.add(tcol)

    return data_map, time_tokens


def _merge_group_labels(group_rows: List[Dict[str, str]], entity_col: str) -> Dict[str, str]:
    """
    Build mapping entity -> group from a Group_lable.csv style file.
    Heuristic: find a column that isn't the entity column and treat it as group label.
    """
    mapping: Dict[str, str] = {}
    if not group_rows:
        return mapping
    if not group_rows[0]:
        return mapping

    # Identify possible group column (first non-entity col)
    sample_headers = list(group_rows[0].keys())
    group_col = None
    for h in sample_headers:
        if h != entity_col:
            group_col = h
            break

    if not group_col:
        return mapping

    for r in group_rows:
        ent = (r.get(entity_col) or "").strip()
        grp = (r.get(group_col) or "").strip()
        if ent:
            mapping[ent] = grp or "ALL"

    return mapping


def _intersect_time_sets(*sets_: Set[str]) -> List[str]:
    if not sets_:
        return []
    common = sets_[0].copy()
    for s in sets_[1:]:
        common &= s
    # Sort numerically if possible, else lexicographically
    def _tkey(tok: str):
        try:
            return float(tok)
        except Exception:
            return tok
    return sorted(common, key=_tkey)


def _write_unified_csv(path: str, rows: List[Dict[str, Any]], headers: List[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({h: r.get(h, "") for h in headers})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def unify_danim_files(
    base_dir: str,
    x_file: str = "X.csv",
    y_file: str = "Y.csv",
    r_file: str = "R.csv",
    group_file: str = "Group_lable.csv",
    output_path: Optional[str] = None,
    entity_col_candidates: Sequence[str] = (
        "Entity", "Country", "Name", "Label", "entity", "country", "name", "label", "ID", "id"
    ),
) -> IngestionResult:
    """
    Ingest Danim-style multiple wide-form CSV files and produce a unified long-form dataset.

    Args:
        base_dir: Directory containing X.csv, Y.csv, R.csv, (optionally Group_lable.csv)
        x_file, y_file, r_file, group_file: Filenames inside base_dir
        output_path: Destination unified CSV file path. If None, defaults to:
                     <base_dir>/unified_dataset.csv
        entity_col_candidates: Candidate entity column names to detect.

    Returns:
        IngestionResult with path to unified CSV and metadata.

    Raises:
        FileNotFoundError if required files are missing.
        ValueError for structural problems (e.g., cannot detect entity column).
    """
    warnings: List[str] = []
    meta: Dict[str, Any] = {}

    # Resolve paths
    x_path = os.path.join(base_dir, x_file)
    y_path = os.path.join(base_dir, y_file)
    r_path = os.path.join(base_dir, r_file)
    g_path = os.path.join(base_dir, group_file)
    if output_path is None:
        output_path = os.path.join(base_dir, "unified_dataset.csv")

    # Read files
    x_rows, x_headers = _safe_read_csv(x_path)
    y_rows, y_headers = _safe_read_csv(y_path)
    r_rows, r_headers = _safe_read_csv(r_path)

    # Detect entity column from X first (most stable)
    entity_col = _detect_entity_column(x_headers, entity_col_candidates)
    if not entity_col:
        raise ValueError(
            f"Could not detect entity column. Expected one of {entity_col_candidates} in {x_headers}"
        )

    # If any file already unified (long-form), handle passthrough scenario.
    # We only support passthrough if ALL three are in unified format — else treat them as wide.
    unified_flags = [
        _is_unified_format(x_headers),
        _is_unified_format(y_headers),
        _is_unified_format(r_headers),
    ]
    if all(unified_flags):
        # Attempt to merge by entity+time keys. Expect columns maybe: entity,time,x,y,r,group
        warnings.append("All input files appear to be unified already; merging by (entity,time).")
        # Build maps
        def _long_map(rows: List[Dict[str, str]], value_col_candidates: Sequence[str]) -> Dict[Tuple[str, str], float]:
            out: Dict[Tuple[str, str], float] = {}
            for rr in rows:
                ent = (rr.get("entity") or "").strip()
                t = (rr.get("time") or "").strip()
                if not ent or not t:
                    continue
                for vc in value_col_candidates:
                    if vc in rr and rr[vc].strip():
                        try:
                            out[(ent, t)] = float(rr[vc])
                            break
                        except ValueError:
                            pass
            return out

        x_map = _long_map(x_rows, ("x",))
        y_map = _long_map(y_rows, ("y",))
        r_map = _long_map(r_rows, ("r",))
        entities = sorted({e for (e, _t) in x_map.keys() | y_map.keys() | r_map.keys()})
        times = sorted({t for (_e, t) in x_map.keys() | y_map.keys() | r_map.keys()})

        unified_rows: List[Dict[str, Any]] = []
        for e in entities:
            for t in times:
                key = (e, t)
                x_val = x_map.get(key)
                y_val = y_map.get(key)
                r_val = r_map.get(key)
                if x_val is None or y_val is None or r_val is None:
                    continue
                unified_rows.append({
                    "entity": e,
                    "time": t,
                    "x": x_val,
                    "y": y_val,
                    "r": r_val,
                    "group": "",  # will fill later if group unified file found
                })
        # Merge group if available
        group_map = {}
        if os.path.exists(g_path):
            try:
                g_rows, g_headers = _safe_read_csv(g_path)
                grp_entity_col = _detect_entity_column(g_headers, (entity_col, "entity", "Entity", "Country"))
                if grp_entity_col:
                    group_map = _merge_group_labels(g_rows, grp_entity_col)
                else:
                    warnings.append("Could not detect entity column in group file; skipping group merge.")
            except Exception as e:
                warnings.append(f"Failed to process group file: {e}")

        for row in unified_rows:
            ent = row["entity"]
            row["group"] = group_map.get(ent, "ALL")

        _write_unified_csv(output_path, unified_rows, ["entity", "time", "x", "y", "r", "group"])
        return IngestionResult(
            unified_path=output_path,
            rows_count=len(unified_rows),
            entities_count=len(entities),
            times_count=len(times),
            columns=["entity", "time", "x", "y", "r", "group"],
            warnings=warnings,
            metadata={"mode": "passthrough-long-form"},
        )

    # Wide-form path:
    x_data, x_times = _parse_wide(x_rows, entity_col)
    y_data, y_times = _parse_wide(y_rows, entity_col)
    r_data, r_times = _parse_wide(r_rows, entity_col)

    if not x_times or not y_times or not r_times:
        raise ValueError("No time columns detected in one or more wide-form files.")

    # Intersect times across all three sets
    common_times = _intersect_time_sets(x_times, y_times, r_times)
    if not common_times:
        raise ValueError("No overlapping time columns between X/Y/R datasets.")

    # Entities union (only keep those present in all three for robustness)
    entities_all = set(x_data.keys()) & set(y_data.keys()) & set(r_data.keys())
    if not entities_all:
        raise ValueError("No common entities across X/Y/R datasets after parsing.")

    # Group labels (optional)
    group_map: Dict[str, str] = {}
    if os.path.exists(g_path):
        try:
            g_rows, g_headers = _safe_read_csv(g_path)
            grp_entity_col = _detect_entity_column(g_headers, entity_col_candidates)
            if grp_entity_col:
                group_map = _merge_group_labels(g_rows, grp_entity_col)
            else:
                warnings.append("Could not detect entity column in group file; skipping group merge.")
        except Exception as e:
            warnings.append(f"Failed to process group file: {e}")
    else:
        warnings.append("Group file not found; assigning ALL as group for each entity.")

    # Build unified rows
    unified_rows: List[Dict[str, Any]] = []
    skipped_missing = 0
    for ent in sorted(entities_all):
        grp = group_map.get(ent, "ALL")
        for t in common_times:
            xv = x_data.get(ent, {}).get(t)
            yv = y_data.get(ent, {}).get(t)
            rv = r_data.get(ent, {}).get(t)
            # Skip if any missing
            if xv is None or yv is None or rv is None:
                skipped_missing += 1
                continue
            unified_rows.append({
                "entity": ent,
                "time": t,
                "x": xv,
                "y": yv,
                "r": rv,
                "group": grp,
            })

    if skipped_missing > 0:
        warnings.append(f"Skipped {skipped_missing} (entity,time) rows with missing x/y/r values.")

    _write_unified_csv(output_path, unified_rows, ["entity", "time", "x", "y", "r", "group"])

    return IngestionResult(
        unified_path=output_path,
        rows_count=len(unified_rows),
        entities_count=len(entities_all),
        times_count=len(common_times),
        columns=["entity", "time", "x", "y", "r", "group"],
        warnings=warnings,
        metadata={
            "mode": "wide-form",
            "input_files": {
                "x": x_path,
                "y": y_path,
                "r": r_path,
                "group": g_path if os.path.exists(g_path) else None,
            },
            "entity_column": entity_col,
            "time_intersection_count": len(common_times),
        },
    )


__all__ = [
    "IngestionResult",
    "unify_danim_files",
]
