"""
Smart Chart Type Inference Module

Analyzes data structure + user intent to recommend the best chart type.
This replaces the simple keyword-only approach with a data-first strategy.

Usage:
    from agents.tools.chart_inference import recommend_chart, analyze_schema

    # Get recommendations for a dataset
    recommendations = recommend_chart(
        csv_path="/path/to/data.csv",
        user_prompt="show me ranking over time"
    )

    # Best recommendation
    best = recommendations[0]
    print(f"Recommended: {best.chart_type} (score: {best.score})")
    print(f"Reasons: {best.reasons}")
"""

from __future__ import annotations

import re
import os
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

# We'll use pandas for data analysis
try:
    import pandas as pd
except ImportError:
    pd = None  # Handle gracefully if pandas not available

# Setup logging
_logger = logging.getLogger("chart_inference")
_logger.setLevel(logging.DEBUG)
if not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))
    _logger.addHandler(handler)


def _log(level: str, message: str, context: dict = None):
    """Internal logging helper."""
    context = context or {}
    log_msg = f"[chart_inference] {message}"
    if context:
        log_msg += f" | {context}"

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR
    }
    _logger.log(level_map.get(level.upper(), logging.INFO), log_msg)


def _resolve_csv_path(csv_path: str) -> str:
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
    if csv_path.startswith("/static/"):
        artifacts_root = os.path.join(os.getcwd(), "artifacts")
        rel_inside = csv_path[len("/static/"):].lstrip("/")
        fs_candidate = os.path.join(artifacts_root, rel_inside)
        if os.path.exists(fs_candidate):
            _log("DEBUG", "Resolved static path to filesystem", {
                "original": csv_path,
                "resolved": fs_candidate,
            })
            return fs_candidate
    return csv_path


def _detect_header_row(filepath: str, max_rows_to_check: int = 10) -> int:
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
    import csv

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
            _log("DEBUG", "Detected header row", {
                "header_row": best_row,
                "score": best_score,
                "filepath": os.path.basename(filepath),
            })
            return best_row

        return 0

    except Exception as e:
        _log("WARNING", f"Header detection failed: {e}", {"filepath": filepath})
        return 0


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DataSchema:
    """
    Analyzed structure of the dataset.

    This tells us WHAT the data looks like, which determines
    what visualizations are possible.
    """
    # Basic info
    columns: List[str]
    column_types: Dict[str, str]  # column -> "numeric" | "categorical" | "temporal"
    row_count: int
    unique_counts: Dict[str, int]  # column -> number of unique values

    # Derived properties (computed from above)
    has_time: bool = False
    time_column: Optional[str] = None
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    entity_count: int = 0  # max unique values in categorical columns

    # Data shape detection
    is_wide_format: bool = False  # True if data has year columns (2000, 2001, ...)
    value_range: Optional[Tuple[float, float]] = None  # (min, max) of numeric values


@dataclass
class ChartRecommendation:
    """
    A recommendation for a specific chart type.

    Includes score, confidence, and explanations so the user
    understands WHY this chart was recommended.
    """
    chart_type: str
    score: float  # 0.0 - 1.0 (higher = better fit)
    confidence: str  # "high" | "medium" | "low"
    reasons: List[str]  # Why this chart fits well
    warnings: List[str]  # Potential issues or limitations

    # For debugging/transparency
    data_requirements_met: Dict[str, bool] = field(default_factory=dict)

    def __post_init__(self):
        """Log recommendation creation."""
        _log("DEBUG", f"ChartRecommendation created", {
            "chart_type": self.chart_type,
            "score": self.score,
            "confidence": self.confidence,
            "reasons_count": len(self.reasons),
            "warnings_count": len(self.warnings),
        })


# =============================================================================
# CHART REQUIREMENTS
# =============================================================================

# Each chart type has specific data requirements
# This makes it easy to add new chart types in the future

CHART_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "bubble": {
        "description": "Multi-dimensional scatter plot with size encoding",
        "min_numeric": 3,  # Need x, y, and r (radius/size)
        "needs_time": True,  # Animation over time
        "needs_entity": True,  # Individual items to track
        "ideal_entity_range": (5, 100),  # Best with 5-100 entities
        "use_cases": ["correlation", "multi-variable comparison", "population studies"],
    },
    "bar_race": {
        "description": "Animated ranking bars racing over time",
        "min_numeric": 1,  # Just need one value to rank
        "needs_time": True,  # Animation over time
        "needs_entity": True,  # Items that compete
        "ideal_entity_range": (5, 50),  # Best with 5-50 entities
        "use_cases": ["rankings", "competition", "market share", "top N"],
    },
    "line_evolution": {
        "description": "Line chart showing trends over time",
        "min_numeric": 1,  # Value to track
        "needs_time": True,  # Time axis
        "needs_entity": True,  # Series to compare
        "ideal_entity_range": (2, 15),  # Too many lines = messy
        "use_cases": ["trends", "growth", "comparison over time"],
    },
    "distribution": {
        "description": "Histogram or density plot showing value distribution",
        "min_numeric": 1,  # Values to distribute
        "needs_time": False,  # Can animate over time, but not required
        "needs_entity": False,  # Can group by entity, but not required
        "ideal_entity_range": (0, 1000),  # Flexible
        "use_cases": ["spread", "frequency", "histogram", "density"],
    },
    "bento_grid": {
        "description": "Dashboard grid showing multiple KPIs",
        "min_numeric": 2,  # Multiple metrics to display
        "needs_time": False,  # Typically snapshot, not time series
        "needs_entity": False,  # Can show multiple entities
        "ideal_entity_range": (1, 20),  # Limited grid space
        "use_cases": ["dashboard", "KPI summary", "metrics overview"],
    },
    "count_bar": {
        "description": "Horizontal bar chart showing counts of categorical values",
        "min_numeric": 0,  # No numeric columns needed - we count occurrences
        "needs_time": False,  # Static snapshot, not time series
        "needs_entity": False,  # Categories become the entities
        "needs_categorical": True,  # Must have at least one categorical column
        "ideal_entity_range": (3, 30),  # Best with 3-30 categories
        "use_cases": ["category counts", "frequency", "distribution", "categorical only"],
    },
    "single_numeric": {
        "description": "Horizontal bar chart showing values per category",
        "min_numeric": 1,  # Exactly one numeric column for values
        "max_numeric": 1,  # Not designed for multiple numeric columns
        "needs_time": False,  # Static snapshot, not time series
        "needs_entity": True,  # Categories/entities to show
        "needs_categorical": True,  # Must have categorical column for labels
        "ideal_entity_range": (3, 20),  # Best with 3-20 categories
        "use_cases": ["values by category", "simple bar chart", "revenue", "population", "scores"],
    },
}


# =============================================================================
# INTENT PATTERNS (User's goal/language)
# =============================================================================

# These patterns detect WHAT the user wants to communicate
# Not just chart names, but semantic intent

INTENT_PATTERNS: Dict[str, List[str]] = {
    "bar_race": [
        # Competition/Ranking intent
        r"\b(rank(ing)?|peringkat|top\s*\d+|leaderboard)\b",
        r"\b(compar(e|ing|ison)|banding(kan)?|versus|vs)\b",
        r"\b(race|racing|compete|competition|lomba)\b",
        r"\b(rise|fall|overtake|surpass|naik|turun)\b",
        # Explicit chart name
        r"\bbar\s*(chart\s*)?race\b",
        r"\bracing\s*bar\b",
    ],
    "line_evolution": [
        # Trend/Change intent
        r"\b(trend|tren|trajectory|path)\b",
        r"\b(evolution|evolusi|perkembangan)\b",
        r"\b(grow(th)?|decline|change|perubahan)\b",
        r"\b(over\s*time|time\s*series|dari\s*waktu\s*ke\s*waktu)\b",
        # Explicit chart name
        r"\bline\s*(chart|graph|evolution)?\b",
        r"\bgrafik\s*garis\b",
    ],
    "bubble": [
        # Multi-dimensional intent
        r"\b(relationship|correlation|korelasi|hubungan)\b",
        r"\b(x\s*(vs?|versus)\s*y|scatter)\b",
        r"\b(size|radius|magnitude|ukuran)\b",
        r"\b(multi.?dimensional|3\s*variables?)\b",
        # Explicit chart name
        r"\bbubble\s*(chart)?\b",
        r"\bgelembung\b",
    ],
    "distribution": [
        # Spread/Shape intent
        r"\b(distribution|distribusi|spread|sebaran)\b",
        r"\b(histogram|frequency|frekuensi)\b",
        r"\b(density|kepadatan|kde)\b",
        r"\b(normal|skew|outlier)\b",
        # Explicit chart name
        r"\bdistribution\s*(chart|plot)?\b",
    ],
    "bento_grid": [
        # Overview/Summary intent
        r"\b(dashboard|overview|summary|ringkasan)\b",
        r"\b(kpi|metric(s)?|key\s*indicator)\b",
        r"\b(at\s*a\s*glance|snapshot|quick\s*view)\b",
        r"\b(grid|panel|tile)\b",
        # Explicit chart name
        r"\bbento\s*(grid|box)?\b",
    ],
    "count_bar": [
        # Counting/Frequency intent
        r"\b(count(s|ing)?|hitung(an)?|jumlah)\b",
        r"\b(frequency|frekuensi|occurrences?)\b",
        r"\b(how\s*many|berapa\s*banyak)\b",
        r"\b(categor(y|ies|ical)|kategori)\b",
        r"\b(breakdown|by\s+category)\b",
        # Explicit chart name
        r"\bcount\s*(bar|chart)?\b",
        r"\bbar\s*chart\b(?!\s*race)",  # bar chart but not bar chart race
        r"\bhorizontal\s*bar\b",
    ],
    "single_numeric": [
        # Value-per-category intent
        r"\b(value|nilai|amount|jumlah)\s*(by|per|untuk)\b",
        r"\b(revenue|sales|penjualan)\s*(by|per)\b",
        r"\b(population|populasi)\s*(by|per)\b",
        r"\b(score|skor)\s*(by|per)\b",
        r"\b(total|sum)\s*(by|per)\b",
        r"\b(show|tampilkan)\s*(the\s*)?(values?|data)\b",
        # Simple bar chart (not race, not count)
        r"\bsimple\s*bar\s*(chart)?\b",
        r"\bbar\s*(chart|graph)\b(?!\s*race)",
        # Explicit chart name
        r"\bsingle\s*numeric\b",
    ],
}


# =============================================================================
# DATA ANALYSIS FUNCTIONS
# =============================================================================

def _is_year_column(series: "pd.Series") -> bool:
    """Check if a column contains year-like values (e.g., 2000, 2001, ...)"""
    _log("DEBUG", f"Checking if column is year-like", {"column": series.name})
    if pd is None:
        return False

    try:
        # Check if values look like years
        numeric_vals = pd.to_numeric(series.dropna(), errors='coerce')
        valid = numeric_vals.dropna()

        if len(valid) == 0:
            return False

        # Years are typically 4 digits between 1900-2100
        in_year_range = (valid >= 1900) & (valid <= 2100)
        return in_year_range.mean() > 0.8  # 80% must be year-like
    except Exception:
        return False


def _is_temporal_column(col_name: str, series: "pd.Series") -> bool:
    """Check if a column is temporal (time-based)"""
    # Check by column name
    temporal_names = ["time", "year", "date", "period", "tahun", "periode", "t", "month", "bulan"]
    if col_name.lower().strip() in temporal_names:
        return True

    # Check if column name is a pattern like "year", "yr", etc.
    if re.match(r"^(year|yr|date|time|periode?|tahun)$", col_name.lower().strip()):
        return True

    # Check content for year-like values
    if _is_year_column(series):
        return True

    return False


def _detect_wide_format(df: "pd.DataFrame") -> Tuple[bool, List[str]]:
    """
    Detect if data is in wide format (entity + year columns).

    Wide format example:
        Country, 2000, 2001, 2002, ...
        USA,     100,  110,  120, ...

    Returns: (is_wide, year_columns)
    """
    year_columns = []

    for col in df.columns:
        col_str = str(col).strip()
        # Check if column name is a year (4 digits)
        if re.match(r"^(19|20)\d{2}$", col_str):
            year_columns.append(col)

    # If we have multiple year columns, it's likely wide format
    is_wide = len(year_columns) >= 3

    return is_wide, year_columns


def analyze_schema(csv_path: str, sample_rows: int = 500) -> DataSchema:
    """
    Analyze CSV structure to understand what charts are possible.

    This is the core function that examines the data and extracts
    key properties needed for chart recommendation.

    Args:
        csv_path: Path to the CSV file (can be /static/... URL or filesystem path)
        sample_rows: Number of rows to sample (for performance)

    Returns:
        DataSchema with analyzed properties
    """
    start_time = time.time()

    # Resolve /static/... paths to filesystem paths
    resolved_path = _resolve_csv_path(csv_path)

    _log("INFO", "Starting schema analysis", {
        "csv_path": csv_path,
        "resolved_path": resolved_path if resolved_path != csv_path else "(same)",
        "sample_rows": sample_rows,
    })

    if pd is None:
        _log("ERROR", "pandas is not available", {"csv_path": csv_path})
        raise RuntimeError("pandas is required for data analysis")

    if not os.path.exists(resolved_path):
        _log("ERROR", "CSV file not found", {"csv_path": csv_path, "resolved_path": resolved_path})
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Detect the actual header row (handles World Bank and similar formats)
    header_row = _detect_header_row(resolved_path)

    # Read sample of the data
    # IMPORTANT: Use skip_blank_lines=False to match the row indexing from csv.reader
    # which counts all rows including blank ones. Without this, pandas skips blank lines
    # and the header_row index becomes incorrect (off by number of blank lines skipped).
    try:
        # Use utf-8-sig encoding to automatically handle BOM (Byte Order Mark)
        # which is common in World Bank and Excel-exported CSVs
        df = pd.read_csv(resolved_path, nrows=sample_rows, header=header_row, skip_blank_lines=False, encoding='utf-8-sig')
        _log("DEBUG", "CSV file loaded", {
            "csv_path": csv_path,
            "header_row": header_row,
            "rows_loaded": len(df),
            "columns": list(df.columns)[:10],  # First 10 to avoid log spam
            "total_columns": len(df.columns),
        })
    except Exception as e:
        _log("ERROR", f"Failed to read CSV file: {e}", {
            "csv_path": csv_path,
            "error_type": type(e).__name__,
        })
        raise

    if df.empty:
        raise ValueError("CSV file is empty")

    # Analyze each column
    column_types: Dict[str, str] = {}
    numeric_cols: List[str] = []
    categorical_cols: List[str] = []
    time_col: Optional[str] = None

    for col in df.columns:
        # Check if temporal first (by name and content)
        if _is_temporal_column(col, df[col]):
            column_types[col] = "temporal"
            if time_col is None:
                time_col = col
        # Then check if numeric
        elif pd.api.types.is_numeric_dtype(df[col]):
            column_types[col] = "numeric"
            numeric_cols.append(col)
        # Otherwise categorical
        else:
            column_types[col] = "categorical"
            categorical_cols.append(col)

    # Calculate unique counts for each column
    unique_counts = {col: int(df[col].nunique()) for col in df.columns}

    # Entity count = max unique values among categorical columns
    entity_count = 0
    if categorical_cols:
        entity_count = max(unique_counts[c] for c in categorical_cols)

    # Detect wide format
    is_wide, year_cols = _detect_wide_format(df)

    # Calculate value range from numeric columns
    value_range = None
    if numeric_cols:
        all_numeric = pd.concat([df[c] for c in numeric_cols])
        value_range = (float(all_numeric.min()), float(all_numeric.max()))

    elapsed_ms = (time.time() - start_time) * 1000
    _log("INFO", "Schema analysis completed", {
        "csv_path": csv_path,
        "elapsed_ms": round(elapsed_ms, 2),
        "row_count": len(df),
        "column_count": len(df.columns),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "has_time": time_col is not None,
        "time_column": time_col,
        "is_wide_format": is_wide,
        "entity_count": entity_count,
    })

    return DataSchema(
        columns=list(df.columns),
        column_types=column_types,
        row_count=len(df),
        unique_counts=unique_counts,
        has_time=(time_col is not None),
        time_column=time_col,
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        entity_count=entity_count,
        is_wide_format=is_wide,
        value_range=value_range,
    )


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def _score_chart_against_schema(
    schema: DataSchema,
    chart_type: str,
) -> ChartRecommendation:
    """
    Score how well a chart type fits the data schema.

    This is where the magic happens - we check each requirement
    and build up a score with explanations.
    """
    reqs = CHART_REQUIREMENTS.get(chart_type)
    if not reqs:
        return ChartRecommendation(
            chart_type=chart_type,
            score=0.0,
            confidence="low",
            reasons=[],
            warnings=[f"Unknown chart type: {chart_type}"],
        )

    score = 0.0
    reasons: List[str] = []
    warnings: List[str] = []
    requirements_met: Dict[str, bool] = {}

    # --- Check 1: Numeric columns ---
    min_numeric = reqs["min_numeric"]
    max_numeric = reqs.get("max_numeric", None)  # Optional upper limit
    num_count = len(schema.numeric_columns)
    needs_categorical = reqs.get("needs_categorical", False)

    if num_count >= min_numeric:
        # Check if there's a max limit (e.g., single_numeric wants exactly 1)
        if max_numeric is not None and num_count > max_numeric:
            # Too many numeric columns - give partial score
            score += 0.15
            reasons.append(f"~ Has {num_count} numeric column(s) (ideal: {min_numeric}-{max_numeric})")
            warnings.append(f"Has more numeric columns than ideal for this chart type")
            requirements_met["numeric_columns"] = True
        else:
            score += 0.3
            reasons.append(f"✓ Has {num_count} numeric column(s) (need {min_numeric}+)")
            requirements_met["numeric_columns"] = True

            # Bonus: single_numeric is ideal when there's exactly 1 numeric column
            if chart_type == "single_numeric" and num_count == 1:
                score += 0.15
                reasons.append("✓ Exactly 1 numeric column - perfect for simple bar chart")
    elif min_numeric == 0 and needs_categorical:
        # count_bar and similar charts don't need numeric columns
        score += 0.3
        reasons.append("✓ No numeric columns needed (will count occurrences)")
        requirements_met["numeric_columns"] = True
    else:
        warnings.append(f"✗ Need {min_numeric}+ numeric columns, have {num_count}")
        requirements_met["numeric_columns"] = False

    # --- Check 1b: Categorical columns (for count_bar and similar) ---
    if needs_categorical:
        cat_count = len(schema.categorical_columns)
        if cat_count > 0:
            score += 0.25
            reasons.append(f"✓ Has {cat_count} categorical column(s) to count")
            requirements_met["categorical_columns"] = True

            # Bonus: If NO numeric columns, count_bar is the ideal choice
            if num_count == 0:
                score += 0.25
                reasons.append("✓ Categorical-only dataset - perfect for count chart")
        else:
            warnings.append("✗ Needs categorical column for counting")
            requirements_met["categorical_columns"] = False

    # --- Check 2: Time column ---
    if reqs["needs_time"]:
        if schema.has_time:
            score += 0.25
            reasons.append(f"✓ Has time column: '{schema.time_column}'")
            requirements_met["time_column"] = True
        else:
            # For wide format, we can derive time from column names
            if schema.is_wide_format:
                score += 0.20
                reasons.append("✓ Wide format detected (year columns)")
                requirements_met["time_column"] = True
            else:
                warnings.append("✗ Needs time column for animation")
                requirements_met["time_column"] = False
    else:
        # Chart doesn't need time, give partial credit
        score += 0.15
        reasons.append("✓ Time column optional for this chart")
        requirements_met["time_column"] = True

    # --- Check 3: Entity column ---
    if reqs["needs_entity"]:
        if schema.entity_count > 0:
            min_e, max_e = reqs["ideal_entity_range"]

            if min_e <= schema.entity_count <= max_e:
                score += 0.35
                reasons.append(f"✓ Has {schema.entity_count} entities (ideal: {min_e}-{max_e})")
                requirements_met["entity_column"] = True
            elif schema.entity_count < min_e:
                score += 0.15
                reasons.append(f"~ Has {schema.entity_count} entities (below ideal {min_e})")
                requirements_met["entity_column"] = True
            else:  # Above max
                score += 0.20
                reasons.append(f"~ Has {schema.entity_count} entities (above ideal {max_e})")
                warnings.append(f"Consider filtering to top {max_e} for clarity")
                requirements_met["entity_column"] = True
        else:
            warnings.append("✗ No categorical column found for entities")
            requirements_met["entity_column"] = False
    else:
        score += 0.20
        reasons.append("✓ Entity column optional for this chart")
        requirements_met["entity_column"] = True

    # --- Bonus: Wide format is great for bar_race/line_evolution ---
    if schema.is_wide_format and chart_type in ("bar_race", "line_evolution"):
        score += 0.10
        reasons.append("✓ Wide format ideal for time-based animation")

    # --- Bonus: count_bar is ideal when there are no numeric columns ---
    if chart_type == "count_bar" and len(schema.numeric_columns) == 0 and len(schema.categorical_columns) > 0:
        score += 0.15
        reasons.append("✓ Count chart is the best option for categorical-only data")

    # --- Determine confidence level ---
    if score >= 0.75:
        confidence = "high"
    elif score >= 0.50:
        confidence = "medium"
    else:
        confidence = "low"

    return ChartRecommendation(
        chart_type=chart_type,
        score=round(min(score, 1.0), 2),  # Cap at 1.0
        confidence=confidence,
        reasons=reasons,
        warnings=warnings,
        data_requirements_met=requirements_met,
    )


def _match_intent_patterns(text: str, chart_type: str) -> float:
    """
    Check how well user's text matches intent patterns for a chart type.

    Returns: Score from 0.0 to 1.0
    """
    if not text:
        return 0.0

    patterns = INTENT_PATTERNS.get(chart_type, [])
    if not patterns:
        return 0.0

    text_lower = text.lower()
    matches = 0

    for pattern in patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matches += 1

    # Normalize: more matches = higher score, but cap at 1.0
    return min(matches * 0.3, 1.0)


# =============================================================================
# MAIN RECOMMENDATION FUNCTION
# =============================================================================

def recommend_chart(
    csv_path: str,
    user_prompt: Optional[str] = None,
    sample_rows: int = 500,
) -> List[ChartRecommendation]:
    """
    Recommend chart types based on data structure + user intent.

    This is the main entry point. It:
    1. Analyzes the data schema
    2. Scores each chart type against the data
    3. Optionally boosts scores based on user intent keywords
    4. Returns sorted recommendations (best first)

    Args:
        csv_path: Path to the CSV file
        user_prompt: Optional user message/prompt for intent detection
        sample_rows: Number of rows to sample for analysis

    Returns:
        List of ChartRecommendation, sorted by score (highest first)

    Example:
        >>> recs = recommend_chart("/data/gdp.csv", "show me top countries")
        >>> print(recs[0].chart_type)  # "bar_race"
        >>> print(recs[0].score)       # 0.92
        >>> print(recs[0].reasons)     # ["✓ Has time column", ...]
    """
    start_time = time.time()
    _log("INFO", "Starting chart recommendation", {
        "csv_path": csv_path,
        "has_user_prompt": bool(user_prompt),
        "prompt_length": len(user_prompt) if user_prompt else 0,
        "sample_rows": sample_rows,
    })

    try:
        # Step 1: Analyze the data
        schema = analyze_schema(csv_path, sample_rows)
        _log("DEBUG", "Schema analysis completed for recommendation", {
            "has_time": schema.has_time,
            "numeric_count": len(schema.numeric_columns),
            "categorical_count": len(schema.categorical_columns),
            "entity_count": schema.entity_count,
        })
    except Exception as e:
        _log("ERROR", f"Failed to analyze schema: {e}", {
            "csv_path": csv_path,
            "error_type": type(e).__name__,
        })
        raise

    # Step 2: Score each chart type
    recommendations: List[ChartRecommendation] = []

    for chart_type in CHART_REQUIREMENTS.keys():
        rec = _score_chart_against_schema(schema, chart_type)

        # Step 3: Boost score based on user intent
        if user_prompt:
            intent_score = _match_intent_patterns(user_prompt, chart_type)
            if intent_score > 0:
                # Add up to 0.15 bonus for matching intent
                bonus = intent_score * 0.15
                rec.score = round(min(rec.score + bonus, 1.0), 2)
                rec.reasons.append(f"✓ User intent matches '{chart_type}' keywords")

                # Upgrade confidence if intent matches
                if rec.confidence == "medium" and intent_score >= 0.3:
                    rec.confidence = "high"

        recommendations.append(rec)

    # Step 4: Sort by score (highest first)
    recommendations.sort(key=lambda r: r.score, reverse=True)

    elapsed_ms = (time.time() - start_time) * 1000
    _log("INFO", "Chart recommendation completed", {
        "csv_path": csv_path,
        "elapsed_ms": round(elapsed_ms, 2),
        "top_recommendation": recommendations[0].chart_type if recommendations else None,
        "top_score": recommendations[0].score if recommendations else None,
        "top_confidence": recommendations[0].confidence if recommendations else None,
        "all_scores": {r.chart_type: r.score for r in recommendations},
    })

    return recommendations


def get_best_chart(
    csv_path: str,
    user_prompt: Optional[str] = None,
    min_confidence: str = "medium",
) -> Optional[ChartRecommendation]:
    """
    Get the single best chart recommendation.

    Convenience function that returns the top recommendation
    if it meets the minimum confidence threshold.

    Args:
        csv_path: Path to CSV file
        user_prompt: Optional user message
        min_confidence: Minimum required confidence ("low", "medium", "high")

    Returns:
        Best ChartRecommendation or None if no good match
    """
    recommendations = recommend_chart(csv_path, user_prompt)

    if not recommendations:
        return None

    best = recommendations[0]

    # Check confidence threshold
    confidence_order = ["low", "medium", "high"]
    if confidence_order.index(best.confidence) >= confidence_order.index(min_confidence):
        return best

    return None


def get_schema_summary(csv_path: str) -> Dict[str, Any]:
    """
    Get a human-readable summary of the data schema.

    Useful for debugging or showing users what was detected.
    """
    schema = analyze_schema(csv_path)

    return {
        "columns": schema.columns,
        "row_count": schema.row_count,
        "has_time": schema.has_time,
        "time_column": schema.time_column,
        "numeric_columns": schema.numeric_columns,
        "categorical_columns": schema.categorical_columns,
        "entity_count": schema.entity_count,
        "is_wide_format": schema.is_wide_format,
        "column_types": schema.column_types,
    }


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Data structures
    "DataSchema",
    "ChartRecommendation",
    # Configuration
    "CHART_REQUIREMENTS",
    "INTENT_PATTERNS",
    # Functions
    "analyze_schema",
    "recommend_chart",
    "get_best_chart",
    "get_schema_summary",
]
