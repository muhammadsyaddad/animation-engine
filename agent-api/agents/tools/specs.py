"""
ChartSpec dataclasses and simple spec inference from prompt.

This module defines a minimal schema to describe an animated chart specification
for our Manim-based pipeline, along with a lightweight heuristic to infer a
reasonable default spec from a natural language prompt.

Updated to support all 5 chart types:
- bubble: Multi-dimensional scatter with size encoding
- distribution: Histogram/density plots
- bar_race: Animated ranking bars over time
- line_evolution: Line chart trends over time
- bento_grid: Dashboard grid with KPIs

Design goals:
- Standard-library only (no external dependencies).
- Conservative inference rules that produce stable defaults.
- Compatible with all chart templates.

Example:
    from agents.tools.specs import infer_spec_from_prompt

    spec = infer_spec_from_prompt("Animasi bubble chart populasi per tahun")
    # Use `spec` to drive code generation or template selection
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Literal, Tuple
import re


# =============================================================================
# CONSTANTS
# =============================================================================

# A simple, readable color palette for group mapping (web hex colors).
DEFAULT_GROUP_COLOR_MAP: Dict[str, str] = {
    "AFRICA": "#F44336",  # RED
    "ASIA": "#4CAF50",  # GREEN
    "EUROPE": "#2196F3",  # BLUE
    "LATIN AMERICA AND THE CARIBBEAN": "#FFEB3B",  # YELLOW
    "OCEANIA": "#9C27B0",  # PURPLE
}

# Supported chart types - now includes all 5 types
ChartType = Literal["bubble", "distribution", "bar_race", "line_evolution", "bento_grid", "unknown"]


# =============================================================================
# DATACLASSES (Spec Schema)
# =============================================================================

@dataclass
class DataBinding:
    """
    Column bindings for datasets.

    For bubble:
      - x_col: numeric (e.g., life expectancy)
      - y_col: numeric (e.g., fertility)
      - r_col: numeric (bubble area proxy, e.g., population)
      - time_col: temporal or discrete step (e.g., year)
      - group_col: optional categorical (e.g., region)
      - entity_col: entity/name identifier (e.g., country/name/label)

    For distribution:
      - value_col: numeric
      - time_col: temporal or discrete step
      - group_col: optional categorical
      - entity_col: optional identifier if relevant

    For bar_race:
      - value_col: numeric (value to rank by)
      - time_col: temporal (for animation)
      - entity_col: entities that compete/race

    For line_evolution:
      - value_col: numeric (y-axis value)
      - time_col: temporal (x-axis)
      - entity_col: series/lines to plot

    For bento_grid:
      - value_col: numeric (metric values)
      - entity_col: metric names/labels
    """
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    r_col: Optional[str] = None
    value_col: Optional[str] = None
    time_col: Optional[str] = None
    group_col: Optional[str] = None
    entity_col: Optional[str] = None


@dataclass
class AxesSpec:
    """
    Axes configuration, compatible with all visualization types.
    """
    auto: bool = True
    x_min: Optional[float] = None
    x_max: Optional[float] = None
    y_min: Optional[float] = None
    y_max: Optional[float] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    x_decimals: int = 0
    y_decimals: int = 0
    show_numbers: bool = True
    show_axis_labels: bool = True


@dataclass
class StyleSpec:
    """
    Visual style, palette, and legend behavior.
    """
    color_map: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_GROUP_COLOR_MAP))
    fill_opacity: float = 0.7
    stroke_width: float = 1.5
    show_legend: bool = True
    legend_position: str = "top-right"  # top-right | top-left | bottom-right | bottom-left
    label_language: Optional[str] = None  # "id" | "en" | "cn" | None


@dataclass
class TimingSpec:
    """
    Animation timing parameters inspired by Danim defaults.
    """
    total_time: float = 30.0
    creation_time: float = 2.0
    transform_ratio: float = 0.3  # fraction of (total_time - creation_time) used for transforms
    lag_ratio: float = 0.3
    max_circles_per_batch: int = 60


@dataclass
class ChartSpec:
    """
    Unified chart spec used by the animation pipeline.

    Fields:
      - chart_type: "bubble" | "distribution" | "bar_race" | "line_evolution" | "bento_grid" | "unknown"
      - data_binding: column bindings
      - axes: axis config
      - creation_mode: 1|2|3 (primarily for bubble charts)
        1: create everything at once
        2: create bubble one-by-one (random order)
        3: create bubble one-by-one grouped by color/group
      - style: visual style config
      - timing: animation timing config
    """
    chart_type: ChartType = "unknown"
    data_binding: DataBinding = field(default_factory=DataBinding)
    axes: AxesSpec = field(default_factory=AxesSpec)
    creation_mode: int = 2
    style: StyleSpec = field(default_factory=StyleSpec)
    timing: TimingSpec = field(default_factory=TimingSpec)

    def to_dict(self) -> Dict:
        return asdict(self)


# =============================================================================
# REGEX PATTERNS FOR CHART TYPE DETECTION
# =============================================================================

_RE_BUBBLE = re.compile(
    r"(?:\bbubble\s*chart\b|\bbubblechart\b|\bbubble\b|\bgelembung\b|\bscatter\b|\bsebar\b)",
    re.IGNORECASE,
)

_RE_DISTRIBUTION = re.compile(
    r"(?:\bdistribution\b|\bdistribusi\b|\bhistogram\b|\bkde\b|\bdensity\b)",
    re.IGNORECASE,
)

_RE_BAR_RACE = re.compile(
    r"(?:\bbar\s*race\b|\bracing\s*bar\b|\branking\b|\bperingkat\b|\btop\s*\d+\b|\bleaderboard\b)",
    re.IGNORECASE,
)

_RE_LINE_EVOLUTION = re.compile(
    r"(?:\bline\s*chart\b|\bline\s*evolution\b|\bline\s*graph\b|\btrend\b|\btren\b|\btime\s*series\b|\bevolution\b|\bevolusi\b)",
    re.IGNORECASE,
)

_RE_BENTO_GRID = re.compile(
    r"(?:\bbento\b|\bdashboard\b|\bkpi\b|\bmetric\b|\boverview\b|\bsummary\b|\bringkasan\b)",
    re.IGNORECASE,
)

# Creation mode patterns
_RE_MODE1 = re.compile(r"(?:\bmode\s*1\b|\boption\s*1\b|\bdirect(ly)?\b|\blangsung\b)", re.IGNORECASE)
_RE_MODE3 = re.compile(
    r"(?:\bmode\s*3\b|\boption\s*3\b|\b(group(ed)?|kelompok)\b|\bby\s*group\b)",
    re.IGNORECASE,
)
_RE_MODE2 = re.compile(r"(?:\bmode\s*2\b|\boption\s*2\b|\brandom\b)", re.IGNORECASE)

# Common label tokens (ID/EN) to set default axis labels
_RE_LIFE_EXPECTANCY = re.compile(r"(life\s*expectancy|umur\s*harapan\s*hidup|人均寿命)", re.IGNORECASE)
_RE_FERTILITY = re.compile(r"(fertilit(y|as)|生育率)", re.IGNORECASE)
_RE_POPULATION = re.compile(r"(population|populasi|人口)", re.IGNORECASE)
_RE_YEAR = re.compile(r"(year|tahun|年)", re.IGNORECASE)
_RE_REGION = re.compile(r"(region|wilayah|区域|area|benua)", re.IGNORECASE)


# =============================================================================
# INFERENCE FUNCTIONS
# =============================================================================

def normalize_chart_type(text: Optional[str]) -> ChartType:
    """
    Infer chart type from prompt text.
    Now supports all 5 chart types.
    """
    t = text or ""

    matches = {
        "bubble": bool(_RE_BUBBLE.search(t)),
        "distribution": bool(_RE_DISTRIBUTION.search(t)),
        "bar_race": bool(_RE_BAR_RACE.search(t)),
        "line_evolution": bool(_RE_LINE_EVOLUTION.search(t)),
        "bento_grid": bool(_RE_BENTO_GRID.search(t)),
    }

    # Count how many chart types matched
    matched_types = [k for k, v in matches.items() if v]

    # If exactly one type matched, return it
    if len(matched_types) == 1:
        return matched_types[0]

    # If multiple matched, prefer based on priority
    # (bar_race and line_evolution are most common requests)
    priority = ["bar_race", "line_evolution", "bubble", "distribution", "bento_grid"]
    for chart_type in priority:
        if matches[chart_type]:
            return chart_type

    return "unknown"


def normalize_chart_type_with_data(
    text: Optional[str],
    csv_path: Optional[str] = None,
    auto_select: bool = True,
) -> ChartType:
    """
    Infer chart type using both prompt text AND data analysis.
    This is the preferred function when you have a CSV path.

    Args:
        text: User's natural language prompt
        csv_path: Optional path to CSV for data-driven inference
        auto_select: If False, skip data-driven inference and return "unknown"
                     to allow the pipeline to emit template suggestions instead.
                     This respects the AUTO_SELECT_TEMPLATES setting.
    """
    # First try keyword-based detection
    keyword_result = normalize_chart_type(text)

    # If auto_select is disabled and user didn't explicitly specify a chart type,
    # return "unknown" to trigger the template suggestion flow
    if not auto_select and keyword_result == "unknown":
        return "unknown"

    # If we have a CSV and keyword result is unknown, try data analysis
    if csv_path and keyword_result == "unknown":
        try:
            from agents.tools.chart_inference import get_best_chart

            best = get_best_chart(csv_path, text, min_confidence="medium")
            if best:
                return best.chart_type
        except Exception:
            pass  # Fall back to keyword result

    return keyword_result


def infer_creation_mode(text: Optional[str]) -> int:
    """
    Guess creation mode for bubble charts. Defaults to 2.
    """
    t = text or ""
    if _RE_MODE1.search(t):
        return 1
    if _RE_MODE3.search(t):
        return 3
    if _RE_MODE2.search(t):
        return 2
    # Heuristic: if "group" or "kelompok" mentioned without explicit number, prefer 3
    if re.search(r"(group|kelompok)", t, re.IGNORECASE):
        return 3
    return 2


def infer_axis_labels(text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Very lightweight inference for axis labels (bubble charts).
    If the prompt references known domains (life expectancy, fertility), use them.
    Otherwise, leave as None for templates to handle.
    """
    t = text or ""
    x_label = None
    y_label = None

    # Common pair: X=Life Expectancy, Y=Fertility
    if _RE_LIFE_EXPECTANCY.search(t):
        x_label = "Life Expectancy"
    if _RE_FERTILITY.search(t):
        y_label = "Fertility"

    return x_label, y_label


def default_binding_for_chart(chart_type: ChartType) -> DataBinding:
    """
    Provide default column bindings for each chart type.
    Updated to include all 5 chart types.
    """
    if chart_type == "bubble":
        return DataBinding(
            x_col="x",
            y_col="y",
            r_col="r",
            time_col="time",
            group_col="group",
            entity_col="entity",
        )
    elif chart_type == "distribution":
        return DataBinding(
            value_col="value",
            time_col="time",
            group_col="group",
            entity_col="entity",
        )
    elif chart_type == "bar_race":
        return DataBinding(
            value_col="value",
            time_col="time",
            group_col="group",
            entity_col="category",
        )
    elif chart_type == "line_evolution":
        return DataBinding(
            value_col="value",
            time_col="time",
            group_col="series",
            entity_col="entity",
        )
    elif chart_type == "bento_grid":
        return DataBinding(
            value_col="value",
            time_col=None,  # Bento grid typically doesn't need time
            group_col="category",
            entity_col="metric",
        )
    else:
        # Unknown: provide generic defaults
        return DataBinding(
            x_col="x",
            y_col="y",
            r_col="r",
            value_col="value",
            time_col="time",
            group_col="group",
            entity_col="entity",
        )


def infer_style_language(text: Optional[str]) -> Optional[str]:
    """
    Attempt to infer preferred label language from prompt (very rough).
    """
    t = (text or "").lower()
    if any(k in t for k in ["umur", "tahun", "wilayah", "populasi", "fertilitas"]):
        return "id"
    if any(k in t for k in ["life", "year", "region", "population", "fertility"]):
        return "en"
    if any(k in t for k in ["年", "区域", "人口", "生育率", "人均寿命"]):
        return "cn"
    return None


def build_default_spec(chart_type: ChartType) -> ChartSpec:
    """
    Construct a ChartSpec with reasonable defaults for the given chart type.
    """
    spec = ChartSpec(
        chart_type=chart_type,
        data_binding=default_binding_for_chart(chart_type),
        axes=AxesSpec(),
        creation_mode=2,
        style=StyleSpec(),
        timing=TimingSpec(),
    )
    return spec


def infer_spec_from_prompt(
    prompt: Optional[str],
    csv_path: Optional[str] = None,
    auto_select_templates: bool = True,
) -> ChartSpec:
    """
    Main entry: infer a minimal ChartSpec from the natural language prompt.

    Args:
        prompt: User's natural language prompt
        csv_path: Optional path to CSV for data-driven inference
        auto_select_templates: If False, skip data-driven chart type inference
                               to allow the pipeline to emit template suggestions.
                               This respects the AUTO_SELECT_TEMPLATES setting.

    Returns:
        ChartSpec with inferred settings

    Features:
        - chart_type: bubble/distribution/bar_race/line_evolution/bento_grid/unknown
        - creation_mode (bubble): 1/2/3
        - axes labels (optional)
        - style language (optional)
        - default bindings to guide downstream ingestion

    Note: This does not validate any dataset; it only generates a spec skeleton.
    """
    # Use data-driven inference if CSV path provided
    if csv_path:
        chart_type = normalize_chart_type_with_data(prompt, csv_path, auto_select=auto_select_templates)
    else:
        chart_type = normalize_chart_type(prompt)

    spec = build_default_spec(chart_type)

    # Infer creation mode for bubble charts
    if chart_type == "bubble":
        spec.creation_mode = infer_creation_mode(prompt)

    # Try lightweight axis labels (bubble)
    x_label, y_label = infer_axis_labels(prompt)
    if x_label:
        spec.axes.x_label = x_label
        spec.axes.x_decimals = 0
    if y_label:
        spec.axes.y_label = y_label
        spec.axes.y_decimals = 0

    # Parse explicit column binding overrides from prompt
    try:
        text = prompt or ""
        # Support quoted or unquoted values: x_col=lifeExp, x_col="lifeExp", x_col='lifeExp'
        for key in ["x_col", "y_col", "r_col", "value_col", "time_col", "group_col", "entity_col"]:
            m = re.search(rf"{key}\s*=\s*(\"([^\"]+)\"|'([^']+)'|([A-Za-z0-9_]+))", text, flags=re.IGNORECASE)
            if m:
                val = m.group(2) or m.group(3) or m.group(4)
                if val:
                    setattr(spec.data_binding, key, val)
    except Exception:
        # If parsing fails, keep inferred/default bindings
        pass

    # Infer style language for labels/legend
    lang = infer_style_language(prompt)
    if lang:
        spec.style.label_language = lang

    return spec


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Data structures
    "ChartSpec",
    "DataBinding",
    "AxesSpec",
    "StyleSpec",
    "TimingSpec",
    "ChartType",
    # Main functions
    "infer_spec_from_prompt",
    "normalize_chart_type",
    "normalize_chart_type_with_data",
    "infer_creation_mode",
    "default_binding_for_chart",
    "build_default_spec",
    "infer_axis_labels",
    "infer_style_language",
]
