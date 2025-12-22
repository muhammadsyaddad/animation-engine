import csv
import re
import os
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("animation_pipeline.template.csv_utils")


def detect_header_row(filepath: str, max_row_to_check: int = 10) -> int:
    """
    Detect the most likely header row in a CSV file by scanning the first
    `max_row_to_check` rows and scoring each row based on heuristics:
      - presence of typical header keywords (country, year, value, etc.)
      - number of non-empty columns
      - presence of year-like values in columns

    Returns:
      - integer index of the detected header row (0-based)
      - returns 0 when detection fails or file is empty
    """
    if not os.path.exists(filepath):
        logger.warning(f"[CSV_UTILS] File not found for header detection: {filepath}")
        return 0

    try:
        rows = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i >= max_row_to_check:
                    break
                rows.append(row)

        if not rows:
            return 0

        # common header tokens
        header_patterns = [
            r"country",
            r"name",
            r"code",
            r"indicator",
            r"region",
            r"year",
            r"date",
            r"value",
            r"series",
            r"id",
            r"film",
            r"director",
            r"time",
            r"category",
            r"label",
            r"entity",
            r"salary",
            r"title",
            r"amount",
        ]

        year_pattern = re.compile(r"^(?:19|20)\d{2}$")  # simple year matcher

        best_row = 0
        best_score = -1
        max_cols = 0

        for i, row in enumerate(rows):
            # normalize cells
            stripped = [str(c).strip() for c in row]
            non_empty_cols = [c for c in stripped if c != ""]
            col_count = len(non_empty_cols)

            score = 0

            # reward rows that open up many columns compared to earlier rows
            if col_count > max_cols * 1.5 and col_count >= 3:
                score += 3
            max_cols = max(max_cols, col_count)

            # reward presence of year-like columns
            years_cols = sum(1 for c in stripped if year_pattern.match(c))
            if years_cols >= 2:
                score += 4
            elif years_cols == 1:
                score += 1

            # reward header-like tokens
            header_matches = sum(
                1 for c in stripped if any(re.search(p, c.lower()) for p in header_patterns)
            )
            if header_matches >= 2:
                score += 3
            elif header_matches == 1:
                score += 1

            # small bonus for reasonable number of columns
            if col_count >= 4:
                score += 1

            # penalize rows that look like numeric-only data rows
            numeric_cells = sum(1 for c in stripped if _is_number_like(c))
            if numeric_cells >= max(1, col_count * 0.6):
                score -= 2

            if score > best_score:
                best_score = score
                best_row = i

        if best_score >= 1:
            logger.debug(
                f"[CSV_UTILS] detected header row {best_row} with score {best_score} for {os.path.basename(filepath)}"
            )
            return best_row

    except Exception as e:
        logger.warning(f"[CSV_UTILS] Header detection failed for {filepath}: {e}")

    return 0


def _is_number_like(val: str) -> bool:
    """Small helper to detect numeric-like strings (ints, floats, percentages)."""
    if val is None:
        return False
    v = val.strip().replace(",", "")
    if v.endswith("%"):
        v = v[:-1]
    try:
        float(v)
        return True
    except Exception:
        return False


def read_csv_rows(
    csv_path: str,
    max_rows: Optional[int] = None,
    detect_header: bool = True,
) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Read CSV and return (headers, rows) where rows is a list of dicts mapping
    header -> cell string. This respects a detected header row (if requested)
    so CSVs with metadata rows above the header are supported.

    Args:
      csv_path: Path to CSV file.
      max_rows: Optional maximum number of data rows to load (None = load all).
      detect_header: Whether to try to detect header row (defaults to True).

    Raises:
      FileNotFoundError if file does not exist.

    Returns:
      (headers, rows)
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    header_row = 0
    if detect_header:
        header_row = detect_header_row(csv_path)

    headers: List[str] = []
    rows: List[Dict[str, str]] = []

    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)

            # skip rows until header_row
            for _ in range(header_row):
                try:
                    next(reader)
                except StopIteration:
                    break

            # read header line
            header_line = None
            try:
                header_line = next(reader)
            except StopIteration:
                header_line = None

            if header_line:
                headers = [h.strip() if h is not None else "" for h in header_line]
            else:
                headers = []

            # if headers are empty, create generic column names as fallback
            if not headers:
                # peek one row to count columns
                try:
                    first_data = next(reader)
                    col_count = len(first_data)
                    headers = [f"col_{i}" for i in range(col_count)]
                    # push first_data back into processing
                    _process_rows_iter = iter([first_data] + list(reader))
                    iterator = _process_rows_iter
                except StopIteration:
                    return headers, []
            else:
                iterator = reader

            loaded = 0
            for row in iterator:
                if max_rows is not None and loaded >= max_rows:
                    break

                # normalize row length to headers length
                if len(row) < len(headers):
                    row = list(row) + [""] * (len(headers) - len(row))
                elif len(row) > len(headers):
                    # in case row has more columns than headers, keep extra but name them
                    extra = len(row) - len(headers)
                    for i in range(extra):
                        headers.append(f"extra_{len(headers)+1}")

                row_dict = {headers[i]: (row[i].strip() if row[i] is not None else "") for i in range(len(headers))}
                rows.append(row_dict)
                loaded += 1

    except Exception as e:
        logger.warning(f"[CSV_UTILS] Failed to load CSV {csv_path}: {e}")
        # return whatever we have so caller can handle partial data
        return headers, rows

    logger.info(f"[CSV_UTILS] Loaded {len(rows)} rows with headers: {headers[:10]}{'...' if len(headers) > 10 else ''}")
    return headers, rows


__all__ = ["detect_header_row", "read_csv_rows"]
