"""
Data preprocessing modules for automatic visualization preparation.

Includes:
- WideFormatDetector: Detects "wide" datasets (e.g., country + many year columns or homogeneous numeric columns).
- WideToLongTransformer: Converts wide format to long tidy format (group, time, value).
- VisualScaler: Scales raw numeric values into normalized range (0..1) with optional log scaling logic.
- AnomalyFlagger: Flags (does NOT remove) anomalous points; supports optional visual clamping metadata.

Design Principles:
- Non-destructive: Original values are retained; anomalies are only flagged.
- Extensible: Each component returns structured metadata for downstream animation templates.
- Deterministic Phase 1 implementation (no ML, no LLM calls here).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import pandas as pd
except ImportError:  # Lightweight fallback if pandas is absent
    pd = None  # type: ignore

import csv
import logging

# Setup logging
_logger = logging.getLogger("data_modules")


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

YEAR_REGEX = re.compile(r"^(?:\d{4})$")
QUARTER_REGEX = re.compile(r"^(?:Q[1-4])$", re.IGNORECASE)
NUMERIC_HEADER_REGEX = re.compile(r"^\d+$")


def _is_numeric(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return not (isinstance(value, float) and math.isnan(value))
    try:
        float(str(value).strip())
        return True
    except Exception:
        return False


def _sample_values(series, sample_size: int = 25) -> List[Any]:
    if pd is None:
        return []
    if len(series) == 0:
        return []
    return list(series.head(sample_size).values)


def _headers_sequential_numeric(headers: Sequence[str]) -> bool:
    """
    Heuristic: headers are strictly increasing integers or years.
    """
    numeric_indices = []
    for h in headers:
        if YEAR_REGEX.match(h) or NUMERIC_HEADER_REGEX.match(h):
            try:
                numeric_indices.append(int(re.findall(r"\d+", h)[0]))
            except Exception:
                return False
        else:
            return False
    # Check monotonic non-decreasing sequence
    return all(b >= a for a, b in zip(numeric_indices, numeric_indices[1:]))


def detect_header_row(filepath: str, max_rows_to_check: int = 10) -> int:
    """
    Detect the actual header row in a CSV file.

    World Bank and similar data sources often have metadata rows before
    the actual data table:

        "Data Source","World Development Indicators",
        "Last Updated Date","2025-...",
        <blank line>
        "Country Name","Country Code","Indicator Name",...,1960,1961,...
        "Afghanistan","AFG","Inflation...",...

    This function scans the first few rows to find where the real data starts
    by looking for:
    1. A row with significantly more columns than previous rows
    2. A row containing year-like column headers (1960, 1970, etc.)
    3. A row containing common data column names (Country, Name, Code, etc.)

    Args:
        filepath: Path to the CSV file
        max_rows_to_check: Maximum number of rows to scan

    Returns:
        0-based index of the header row (0 if no special header detected)
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            # Read first N rows
            rows = []
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i >= max_rows_to_check:
                    break
                rows.append(row)

        if not rows:
            return 0

        # Patterns indicating a data header row
        header_patterns = [
            r'country', r'name', r'code', r'indicator', r'region',
            r'year', r'date', r'value', r'series', r'id',
        ]
        year_pattern = re.compile(r'^(19|20)\d{2}$')  # Years like 1960, 2023

        best_row = 0
        best_score = 0
        max_cols = 0

        for i, row in enumerate(rows):
            col_count = len([c for c in row if c.strip()])  # Non-empty columns
            score = 0

            # Score: more columns than previous rows (data tables are wider)
            if col_count > max_cols * 1.5 and col_count >= 4:
                score += 3
            max_cols = max(max_cols, col_count)

            # Score: contains year columns
            year_cols = sum(1 for c in row if year_pattern.match(str(c).strip()))
            if year_cols >= 3:
                score += 5

            # Score: contains header-like column names
            header_matches = sum(
                1 for c in row
                if any(re.search(p, str(c).lower()) for p in header_patterns)
            )
            if header_matches >= 2:
                score += 3

            # Score: row has many columns (at least 5)
            if col_count >= 5:
                score += 1

            if score > best_score:
                best_score = score
                best_row = i

        if best_score >= 3:
            _logger.debug(f"[data_modules] Detected header row {best_row} with score {best_score}")
            return best_row

        return 0

    except Exception as e:
        _logger.warning(f"[data_modules] Header detection failed: {e}")
        return 0


def resolve_csv_path(csv_path: str) -> str:
    """
    Resolve a CSV path that may be a /static/... URL to its filesystem path.

    This handles the common case where the frontend sends paths like:
        /static/datasets/dataset_xxx/file.csv

    But the actual file is at:
        <cwd>/artifacts/datasets/dataset_xxx/file.csv

    Args:
        csv_path: Path that might be a /static/... URL or filesystem path

    Returns:
        Resolved filesystem path
    """
    import os
    if csv_path.startswith("/static/"):
        artifacts_root = os.path.join(os.getcwd(), "artifacts")
        rel_inside = csv_path[len("/static/"):].lstrip("/")
        fs_candidate = os.path.join(artifacts_root, rel_inside)
        if os.path.exists(fs_candidate):
            return fs_candidate
    return csv_path


def read_csv_smart(filepath: str, nrows: Optional[int] = None, **kwargs) -> Any:
    """
    Read a CSV file with smart header detection.

    Handles World Bank and similar formats that have metadata rows before
    the actual data table.

    Args:
        filepath: Path to the CSV file (can be /static/... URL or filesystem path)
        nrows: Number of rows to read (None for all)
        **kwargs: Additional arguments passed to pd.read_csv

    Returns:
        pandas DataFrame with data properly parsed
    """
    if pd is None:
        raise RuntimeError("pandas is required for CSV reading")

    # Resolve path if needed
    resolved_path = resolve_csv_path(filepath)

    # Detect header row
    header_row = detect_header_row(resolved_path)

    # Read with detected header
    # IMPORTANT: Use skip_blank_lines=False to match the row indexing from csv.reader
    # which counts all rows including blank ones. Without this, pandas skips blank lines
    # and the header_row index becomes incorrect (off by number of blank lines skipped).
    read_kwargs = {"header": header_row, "skip_blank_lines": False, **kwargs}
    if nrows is not None:
        read_kwargs["nrows"] = nrows

    try:
        # Use utf-8-sig encoding to automatically handle BOM (Byte Order Mark)
        # which is common in World Bank and Excel-exported CSVs
        df = pd.read_csv(resolved_path, encoding='utf-8-sig', **read_kwargs)
        _logger.debug(f"[data_modules] Read CSV with header_row={header_row}, shape={df.shape}")
        return df
    except UnicodeDecodeError:
        # Try latin-1 encoding as fallback
        df = pd.read_csv(resolved_path, encoding='latin-1', **read_kwargs)
        _logger.debug(f"[data_modules] Read CSV with latin-1 encoding, shape={df.shape}")
        return df


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class WideDetectionResult:
    is_wide: bool
    group_column: Optional[str] = None
    value_columns: List[str] = field(default_factory=list)
    time_like_headers: List[str] = field(default_factory=list)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransformResult:
    df_long: Any  # Expect pandas.DataFrame
    group_col: str
    time_col: str
    value_col: str
    transform_applied: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScaleMetadata:
    method: str  # 'minmax' or 'log-minmax'
    min_value: float
    max_value: float
    epsilon: float
    log_used: bool
    clamped_min: Optional[float] = None
    clamped_max: Optional[float] = None


@dataclass
class ScalingResult:
    df_scaled: Any
    normalized_col: str
    original_col: str
    metadata: ScaleMetadata


@dataclass
class AnomalyReport:
    algorithm: str
    total_points: int
    flagged_points: int
    pct_flagged: float
    threshold: float
    notes: List[str] = field(default_factory=list)


@dataclass
class AnomalyFlagResult:
    df_flagged: Any
    report: AnomalyReport
    anomaly_col: str
    clamped_col: Optional[str] = None


# ---------------------------------------------------------------------------
# Data Validation
# ---------------------------------------------------------------------------

@dataclass
class DataValidationResult:
    """Result of validating a dataset for animation suitability."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    potential_time_column: Optional[str] = None
    potential_group_column: Optional[str] = None
    row_count: int = 0
    column_count: int = 0

    def to_user_message(self) -> str:
        """Generate a user-friendly message explaining validation results."""
        if self.is_valid:
            return "Dataset is valid for animation."

        parts = ["**Dataset Validation Failed**\n"]

        if self.errors:
            parts.append("**Issues found:**")
            for err in self.errors:
                parts.append(f"  • {err}")
            parts.append("")

        if self.suggestions:
            parts.append("**How to fix:**")
            for sug in self.suggestions:
                parts.append(f"  • {sug}")
            parts.append("")

        if self.warnings:
            parts.append("**Warnings:**")
            for warn in self.warnings:
                parts.append(f"  • {warn}")

        return "\n".join(parts)


def validate_for_animation(df, filename: Optional[str] = None) -> DataValidationResult:
    """
    Validate a DataFrame for animation suitability.

    Checks:
    1. Has at least one numeric column (required for most animations)
    2. Has enough rows (at least 2)
    3. Has a potential group/entity column
    4. Has a potential time column (optional but recommended)

    Returns DataValidationResult with detailed feedback.
    """
    if pd is None:
        return DataValidationResult(
            is_valid=False,
            errors=["pandas is not available"],
        )

    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

    row_count = len(df)
    column_count = len(df.columns)

    # Check row count
    if row_count == 0:
        errors.append("Dataset is empty (0 rows)")
        suggestions.append("Upload a CSV file with data rows")
    elif row_count < 2:
        errors.append(f"Dataset has only {row_count} row(s) - need at least 2 for animation")
        suggestions.append("Add more data rows to your CSV")

    # Check column count
    if column_count == 0:
        errors.append("Dataset has no columns")
        return DataValidationResult(
            is_valid=False,
            errors=errors,
            suggestions=["Upload a valid CSV file with headers"],
            row_count=row_count,
            column_count=column_count,
        )

    # Identify numeric and categorical columns
    numeric_cols: List[str] = []
    categorical_cols: List[str] = []

    for col in df.columns:
        # Try to convert to numeric
        numeric_count = pd.to_numeric(df[col], errors='coerce').notna().sum()
        total_non_null = df[col].notna().sum()

        if total_non_null > 0 and numeric_count / total_non_null >= 0.5:
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    # Check for numeric columns
    if not numeric_cols:
        errors.append("No numeric columns found - animations require numeric values to visualize")
        suggestions.append("Add a column with numeric values (e.g., population, sales, count, percentage)")
        suggestions.append(f"Current columns are all text/categorical: {', '.join(df.columns[:5])}" +
                          ("..." if len(df.columns) > 5 else ""))

    # Identify potential time column
    time_col: Optional[str] = None
    time_patterns = ['year', 'date', 'time', 'month', 'day', 'period', 'quarter']

    for col in df.columns:
        col_lower = col.lower()
        # Check name patterns
        if any(p in col_lower for p in time_patterns):
            time_col = col
            break
        # Check if column looks like years (4-digit numbers between 1900-2100)
        if col in numeric_cols:
            sample = df[col].dropna().head(10)
            if len(sample) > 0:
                try:
                    vals = pd.to_numeric(sample, errors='coerce').dropna()
                    if len(vals) > 0 and vals.between(1900, 2100).all():
                        time_col = col
                        break
                except Exception:
                    pass

    if not time_col and numeric_cols:
        warnings.append("No time/date column detected - some animations (bar race, line evolution) work best with time data")
        suggestions.append("Consider adding a 'year', 'date', or 'time' column for time-series animations")

    # Identify potential group column
    group_col: Optional[str] = None
    group_patterns = ['name', 'country', 'region', 'category', 'group', 'entity', 'id', 'label']

    for col in categorical_cols:
        col_lower = col.lower()
        if any(p in col_lower for p in group_patterns):
            group_col = col
            break

    # If no pattern match, use first categorical column with reasonable cardinality
    if not group_col and categorical_cols:
        for col in categorical_cols:
            unique_count = df[col].nunique()
            if 2 <= unique_count <= 100:  # Reasonable number of groups for visualization
                group_col = col
                break

    if not group_col and categorical_cols:
        group_col = categorical_cols[0]  # Fallback to first categorical

    if not group_col and not categorical_cols:
        warnings.append("No categorical/group column found - animations typically group data by category (e.g., country, product)")

    # Additional data quality checks
    if row_count > 0 and column_count > 0:
        null_pct = df.isnull().sum().sum() / (row_count * column_count)
        if null_pct > 0.5:
            warnings.append(f"High percentage of missing values ({null_pct:.0%}) - this may affect visualization quality")

    is_valid = len(errors) == 0

    return DataValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        potential_time_column=time_col,
        potential_group_column=group_col,
        row_count=row_count,
        column_count=column_count,
    )


# ---------------------------------------------------------------------------
# WideFormatDetector
# ---------------------------------------------------------------------------

class WideFormatDetector:
    """
    Detects wide-format datasets where columns after a key/group column represent
    sequential or homogeneous numeric series (e.g., years, periods, Q1..Q4).

    Heuristics:
    1. YEAR PATTERN: Many headers matching YYYY.
    2. SEQUENTIAL NUMERIC HEADERS: e.g., 2000, 2001, 2002...
    3. PERIOD HEADERS: Q1, Q2, Q3, Q4 (≥ 3 present).
    4. HOMOGENEOUS NUMERIC CONTENT: For columns after the first, if ≥ 80% of sampled values
       are numeric across ≥ 70% of those columns, treat as wide.

    Returns a WideDetectionResult with reasoning.
    """

    def __init__(
        self,
        min_wide_columns: int = 5,
        numeric_sample_size: int = 20,
        numeric_column_ratio_threshold: float = 0.7,
        numeric_value_ratio_threshold: float = 0.8,
    ):
        self.min_wide_columns = min_wide_columns
        self.numeric_sample_size = numeric_sample_size
        self.numeric_column_ratio_threshold = numeric_column_ratio_threshold
        self.numeric_value_ratio_threshold = numeric_value_ratio_threshold

    def detect(self, df) -> WideDetectionResult:
        if pd is None:
            return WideDetectionResult(False, reason="pandas not available")

        if df is None or df.empty:
            return WideDetectionResult(False, reason="empty dataframe")

        columns = list(df.columns)
        if len(columns) < 3:
            return WideDetectionResult(False, reason="not enough columns")

        group_col = columns[0]
        candidate_cols = columns[1:]

        reasons = []
        metadata = {}

        # Collect header categories
        year_like = [c for c in candidate_cols if YEAR_REGEX.match(str(c))]
        quarter_like = [c for c in candidate_cols if QUARTER_REGEX.match(str(c))]
        pure_numeric_headers = [c for c in candidate_cols if NUMERIC_HEADER_REGEX.match(str(c))]

        if len(year_like) >= self.min_wide_columns:
            reasons.append(f"Detected {len(year_like)} year-like headers")
        if len(quarter_like) >= 3:
            reasons.append(f"Detected {len(quarter_like)} quarter-like headers")
        if _headers_sequential_numeric(candidate_cols) and len(candidate_cols) >= self.min_wide_columns:
            reasons.append("Headers are sequential numeric")
        if len(pure_numeric_headers) >= self.min_wide_columns:
            reasons.append("Multiple pure numeric headers")

        # Numeric content homogeneity test
        numeric_column_count = 0
        value_ratio_accumulator: List[float] = []
        for col in candidate_cols:
            sample_vals = _sample_values(df[col], self.numeric_sample_size)
            if not sample_vals:
                continue
            numeric_flags = [_is_numeric(v) for v in sample_vals]
            ratio = sum(numeric_flags) / len(numeric_flags)
            value_ratio_accumulator.append(ratio)
            if ratio >= self.numeric_value_ratio_threshold:
                numeric_column_count += 1

        if candidate_cols:
            numeric_column_ratio = numeric_column_count / len(candidate_cols)
        else:
            numeric_column_ratio = 0.0

        metadata.update(
            {
                "year_like_count": len(year_like),
                "quarter_like_count": len(quarter_like),
                "pure_numeric_header_count": len(pure_numeric_headers),
                "numeric_column_ratio": numeric_column_ratio,
                "avg_value_numeric_ratio": (sum(value_ratio_accumulator) / len(value_ratio_accumulator))
                if value_ratio_accumulator
                else 0.0,
                "total_candidate_columns": len(candidate_cols),
            }
        )

        # Decision
        is_wide = False
        if reasons:
            is_wide = True
        elif (
            len(candidate_cols) >= self.min_wide_columns
            and numeric_column_ratio >= self.numeric_column_ratio_threshold
        ):
            reasons.append(
                f"Numeric content homogeneous across columns (ratio={numeric_column_ratio:.2f})"
            )
            is_wide = True

        # If only one reason, ensure minimal threshold of columns
        if is_wide and len(candidate_cols) < self.min_wide_columns:
            is_wide = False
            reasons.append(
                f"Insufficient columns for wide format (found {len(candidate_cols)}, need ≥ {self.min_wide_columns})"
            )

        return WideDetectionResult(
            is_wide=is_wide,
            group_column=group_col if is_wide else None,
            value_columns=candidate_cols if is_wide else [],
            time_like_headers=year_like + quarter_like + pure_numeric_headers,
            reason="; ".join(reasons) if reasons else "No wide pattern detected",
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# WideToLongTransformer
# ---------------------------------------------------------------------------

class WideToLongTransformer:
    """
    Transforms a detected wide DataFrame into long tidy format.

    Output schema:
        group_col: original first column (e.g., 'country')
        time_col: 'time' (normalized header)
        value_col: 'value'

    Notes:
    - Attempt to coerce time headers to numeric when possible (e.g., years).
    - Keeps original header text in a 'raw_time_label' column (optional).
    """

    def __init__(self, time_col_name: str = "time", value_col_name: str = "value"):
        self.time_col_name = time_col_name
        self.value_col_name = value_col_name

    def transform(self, df, detection: WideDetectionResult) -> TransformResult:
        if pd is None:
            return TransformResult(df, "", "", "", False, metadata={"error": "pandas not available"})
        if not detection.is_wide:
            # Return original unchanged
            return TransformResult(
                df_long=df,
                group_col=df.columns[0],
                time_col=None,
                value_col=None,
                transform_applied=False,
                metadata={"reason": "Not wide format"},
            )

        group_col = detection.group_column
        value_cols = detection.value_columns

        # Melt
        long_df = df.melt(
            id_vars=[group_col],
            value_vars=value_cols,
            var_name=self.time_col_name,
            value_name=self.value_col_name,
        )

        # Preserve original time label
        long_df["raw_time_label"] = long_df[self.time_col_name]

        # Try converting time to numeric if all convertible (e.g., years)
        if all(YEAR_REGEX.match(str(v)) or NUMERIC_HEADER_REGEX.match(str(v)) for v in long_df[self.time_col_name].unique()):
            try:
                long_df[self.time_col_name] = long_df[self.time_col_name].astype(int)
            except Exception:
                pass  # keep original string if conversion fails

        # Coerce values to numeric
        long_df[self.value_col_name] = pd.to_numeric(long_df[self.value_col_name], errors="coerce")

        metadata = {
            "rows_before": len(df),
            "rows_after": len(long_df),
            "unique_time_values": long_df[self.time_col_name].nunique(),
            "group_col": group_col,
            "value_cols_original_count": len(value_cols),
        }

        return TransformResult(
            df_long=long_df,
            group_col=group_col,
            time_col=self.time_col_name,
            value_col=self.value_col_name,
            transform_applied=True,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# VisualScaler
# ---------------------------------------------------------------------------

class VisualScaler:
    """
    Scales numeric values into a 0..1 range suitable for Manim coordinate mapping.

    Logic:
    - Decide whether to apply log scaling:
        If value_max / max(value_min, ε) ≥ log_ratio_threshold and value_min > 0.
    - Apply scaling formula:
        Linear: (x - min) / (max - min)
        Log: (log10(x) - log10(min)) / (log10(max) - log10(min))
    - Optionally clamp extreme outliers visually without altering original data:
        Clamped range can be set by specifying clamp_quantiles (e.g., (0.01, 0.99)).

    Returns:
        DataFrame with 'normalized_value' column.
    """

    def __init__(
        self,
        normalized_col_name: str = "normalized_value",
        log_ratio_threshold: float = 100.0,
        epsilon: float = 1e-9,
        clamp_quantiles: Optional[Tuple[float, float]] = None,
    ):
        self.normalized_col_name = normalized_col_name
        self.log_ratio_threshold = log_ratio_threshold
        self.epsilon = epsilon
        self.clamp_quantiles = clamp_quantiles

    def scale(self, df, value_col: str) -> ScalingResult:
        if pd is None:
            return ScalingResult(df, "", value_col, metadata=ScaleMetadata(
                method="none", min_value=0, max_value=0, epsilon=self.epsilon, log_used=False
            ))

        series = df[value_col].dropna()
        if series.empty:
            meta = ScaleMetadata(
                method="none", min_value=0, max_value=0, epsilon=self.epsilon, log_used=False
            )
            df[self.normalized_col_name] = 0.0
            return ScalingResult(df_scaled=df, normalized_col=self.normalized_col_name, original_col=value_col, metadata=meta)

        vmin = float(series.min())
        vmax = float(series.max())
        log_used = False
        method = "minmax"

        # Determine clamping bounds (for visualization, not altering original value_col)
        clamped_min = None
        clamped_max = None
        if self.clamp_quantiles is not None:
            q_low, q_high = self.clamp_quantiles
            clamped_min = float(series.quantile(q_low))
            clamped_max = float(series.quantile(q_high))
        else:
            clamped_min = vmin
            clamped_max = vmax

        # Log scaling decision
        if vmin > 0 and (vmax / max(vmin, self.epsilon)) >= self.log_ratio_threshold:
            log_used = True
            method = "log-minmax"

        # Prepare denominator
        if log_used:
            log_min = math.log10(max(vmin, self.epsilon))
            log_max = math.log10(max(vmax, self.epsilon))
            denom = log_max - log_min if log_max != log_min else 1.0

            def _scale(x: float) -> float:
                if x <= 0:
                    return 0.0
                return (math.log10(x) - log_min) / denom
        else:
            denom = vmax - vmin if vmax != vmin else 1.0

            def _scale(x: float) -> float:
                return (x - vmin) / denom

        # Apply scaling on clamped value (for visual normalization)
        normalized_values: List[float] = []
        for x in df[value_col].values:
            if x is None or (isinstance(x, float) and math.isnan(x)):
                normalized_values.append(float("nan"))
                continue
            original_x = float(x)
            # Visual clamping (non-destructive)
            vis_x = min(max(original_x, clamped_min), clamped_max)
            normalized_values.append(_scale(vis_x))

        df[self.normalized_col_name] = normalized_values

        meta = ScaleMetadata(
            method=method,
            min_value=vmin,
            max_value=vmax,
            epsilon=self.epsilon,
            log_used=log_used,
            clamped_min=clamped_min,
            clamped_max=clamped_max,
        )
        return ScalingResult(
            df_scaled=df,
            normalized_col=self.normalized_col_name,
            original_col=value_col,
            metadata=meta,
        )


# ---------------------------------------------------------------------------
# AnomalyFlagger
# ---------------------------------------------------------------------------

class AnomalyFlagger:
    """
    Flags anomalies without deleting or altering original values.

    Algorithm (rolling median deviation):
    - Sort by (group_col, time_col).
    - Compute rolling window median & std for each group (window >= min_window).
    - Flag point if |value - median| > deviation_factor * rolling_std.
    - If rolling std is zero or NaN, skip flag (not enough variation / insufficient window).

    Optional visual clamping (non-destructive):
    - If clamping enabled, a 'clamped_value' column is produced using quantile-based bounds
      (does not replace original value column).

    Returns an AnomalyFlagResult with metadata.
    """

    def __init__(
        self,
        window: int = 5,
        deviation_factor: float = 3.0,
        anomaly_col_name: str = "is_anomaly",
        clamped_col_name: str = "clamped_value",
        clamp_quantiles: Optional[Tuple[float, float]] = None,
        min_window: int = 3,
    ):
        self.window = window
        self.deviation_factor = deviation_factor
        self.anomaly_col_name = anomaly_col_name
        self.clamped_col_name = clamped_col_name
        self.clamp_quantiles = clamp_quantiles
        self.min_window = min_window

    def flag(self, df, group_col: str, time_col: str, value_col: str) -> AnomalyFlagResult:
        if pd is None:
            report = AnomalyReport(
                algorithm="rolling_median",
                total_points=0,
                flagged_points=0,
                pct_flagged=0.0,
                threshold=self.deviation_factor,
                notes=["pandas not available"],
            )
            return AnomalyFlagResult(df_flagged=df, report=report, anomaly_col=self.anomaly_col_name)

        if df.empty:
            report = AnomalyReport(
                algorithm="rolling_median",
                total_points=0,
                flagged_points=0,
                pct_flagged=0.0,
                threshold=self.deviation_factor,
                notes=["empty dataframe"],
            )
            df[self.anomaly_col_name] = False
            return AnomalyFlagResult(df_flagged=df, report=report, anomaly_col=self.anomaly_col_name)

        work = df.copy()
        work.sort_values([group_col, time_col], inplace=True)

        # Rolling stats per group
        anomaly_flags: List[bool] = []
        group_stats_notes: List[str] = []

        if self.clamp_quantiles is not None:
            q_low, q_high = self.clamp_quantiles
            global_low = float(work[value_col].quantile(q_low))
            global_high = float(work[value_col].quantile(q_high))
            clamped_values = []
        else:
            global_low = None
            global_high = None
            clamped_values = None

        for _, gdf in work.groupby(group_col):
            vals = gdf[value_col].astype(float)
            rolling_med = vals.rolling(self.window, min_periods=self.min_window).median()
            rolling_std = vals.rolling(self.window, min_periods=self.min_window).std()
            for idx, (v, med, sd) in enumerate(zip(vals, rolling_med, rolling_std)):
                if math.isnan(v) or math.isnan(med) or math.isnan(sd) or sd == 0:
                    anomaly_flags.append(False)
                else:
                    diff = abs(v - med)
                    anomaly_flags.append(diff > self.deviation_factor * sd)
            if rolling_std.isna().all():
                group_stats_notes.append(f"Group '{gdf[group_col].iloc[0]}': insufficient data for std")

        work[self.anomaly_col_name] = anomaly_flags

        if clamped_values is not None:
            for v in work[value_col].values:
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    clamped_values.append(v)
                else:
                    clamped_values.append(min(max(float(v), global_low), global_high))
            work[self.clamped_col_name] = clamped_values

        total = len(work)
        flagged = int(work[self.anomaly_col_name].sum())
        pct = flagged / total if total else 0.0

        report = AnomalyReport(
            algorithm="rolling_median",
            total_points=total,
            flagged_points=flagged,
            pct_flagged=pct,
            threshold=self.deviation_factor,
            notes=group_stats_notes,
        )

        return AnomalyFlagResult(
            df_flagged=work,
            report=report,
            anomaly_col=self.anomaly_col_name,
            clamped_col=self.clamped_col_name if clamped_values is not None else None,
        )


# ---------------------------------------------------------------------------
# Orchestrator convenience function
# ---------------------------------------------------------------------------

def preprocess_dataset(
    df,
    filename: Optional[str] = None,
    detector: Optional[WideFormatDetector] = None,
    transformer: Optional[WideToLongTransformer] = None,
    scaler: Optional[VisualScaler] = None,
    anomaly_flagger: Optional[AnomalyFlagger] = None,
) -> Dict[str, Any]:
    """
    High-level convenience wrapper combining all modules deterministically.

    Steps:
    1. Detect wide format.
    2. Transform if wide.
    3. Flag anomalies (non-destructive).
    4. Scale values.
    5. Return structured payload with all metadata.

    Returns a dictionary with keys:
        'data' : processed DataFrame
        'detection'
        'transform'
        'anomalies'
        'scaling'
        'columns'
        'filename'
    """
    if pd is None:
        return {"error": "pandas not available"}

    detector = detector or WideFormatDetector()
    transformer = transformer or WideToLongTransformer()
    scaler = scaler or VisualScaler()
    anomaly_flagger = anomaly_flagger or AnomalyFlagger()

    detection = detector.detect(df)
    transform_res = transformer.transform(df, detection)

    working_df = transform_res.df_long

    # Determine operative columns
    group_col = transform_res.group_col
    time_col = transform_res.time_col or (
        "time" if "time" in working_df.columns else working_df.columns[1]
    )
    value_col = transform_res.value_col or (
        working_df.select_dtypes("number").columns[0]
        if len(working_df.select_dtypes("number").columns) > 0
        else None
    )

    # If no numeric column found, skip anomaly flagging and scaling
    if value_col is None:
        return {
            "data": working_df,
            "detection": detection,
            "transform": transform_res,
            "anomalies": None,
            "scaling": None,
            "columns": {
                "group": group_col,
                "time": time_col,
                "value": None,
                "normalized": None,
                "anomaly_flag": None,
                "clamped_value": None,
            },
            "filename": filename,
            "validation_error": "No numeric columns found - cannot perform anomaly detection or scaling",
        }

    # Anomaly flagging
    anomaly_res = anomaly_flagger.flag(
        working_df, group_col=group_col, time_col=time_col, value_col=value_col
    )
    flagged_df = anomaly_res.df_flagged

    # Scaling
    scaling_res = scaler.scale(flagged_df, value_col=value_col)
    scaled_df = scaling_res.df_scaled

    return {
        "data": scaled_df,
        "detection": detection,
        "transform": transform_res,
        "anomalies": anomaly_res,
        "scaling": scaling_res,
        "columns": {
            "group": group_col,
            "time": time_col,
            "value": value_col,
            "normalized": scaling_res.normalized_col,
            "anomaly_flag": anomaly_res.anomaly_col,
            "clamped_value": anomaly_res.clamped_col,
        },
        "filename": filename,
    }


# ---------------------------------------------------------------------------
# Categorical Count Transformation
# ---------------------------------------------------------------------------

def transform_count_by_column(
    df,
    count_column: str,
    output_path: Optional[str] = None,
    top_n: int = 15,
) -> Dict[str, Any]:
    """
    Transform a categorical dataset into a count aggregation.

    This creates a new DataFrame (and optionally saves CSV) with columns: category, count
    Sorted by count descending.

    Args:
        df: Input DataFrame
        count_column: Column to count occurrences of
        output_path: Optional path to save output CSV
        top_n: Maximum categories to include

    Returns:
        Dictionary with:
            'data': DataFrame with category and count columns
            'categories': List of category names
            'counts': List of count values
            'max_count': Maximum count value
            'total_items': Total number of items counted
            'column_name': Name of the counted column
            'output_path': Path to saved CSV (if output_path was provided)
    """
    if pd is None:
        return {"error": "pandas not available"}

    if count_column not in df.columns:
        # Try case-insensitive match
        col_map = {c.lower(): c for c in df.columns}
        if count_column.lower() in col_map:
            count_column = col_map[count_column.lower()]
        else:
            return {"error": f"Column '{count_column}' not found in DataFrame"}

    # Count occurrences
    counts = df[count_column].value_counts().head(top_n)

    # Create result DataFrame
    result_df = pd.DataFrame({
        "category": counts.index.tolist(),
        "count": counts.values.tolist(),
    })

    # Save to file if path provided
    saved_path = None
    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        result_df.to_csv(output_path, index=False)
        saved_path = output_path

    return {
        "data": result_df,
        "categories": counts.index.tolist(),
        "counts": counts.values.tolist(),
        "max_count": int(counts.max()) if len(counts) > 0 else 0,
        "total_items": int(df[count_column].notna().sum()),
        "column_name": count_column,
        "output_path": saved_path,
    }


__all__ = [
    "WideFormatDetector",
    "WideDetectionResult",
    "WideToLongTransformer",
    "TransformResult",
    "VisualScaler",
    "ScaleMetadata",
    "ScalingResult",
    "AnomalyFlagger",
    "AnomalyReport",
    "AnomalyFlagResult",
    "DataValidationResult",
    "validate_for_animation",
    "preprocess_dataset",
    "transform_count_by_column",
    "detect_header_row",
    "resolve_csv_path",
    "read_csv_smart",
]
