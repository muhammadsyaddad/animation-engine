"""
ChartSpec dataclasses and simple spec inference from prompt.

This module defines a minimal schema to describe an animated chart specification
for our Manim-based pipeline, along with a lightweight heuristic to infer a
reasonable default spec from a natural language prompt.

Design goals:
- Standard-library only (no external dependencies).
- Conservative inference rules that produce stable defaults.
- Compatible with Bubble and Distribution charts (Danim-style targets).

Example:
    from agents.tools.specs import infer_spec_from_prompt

    spec = infer_spec_from_prompt("Animasi bubble chart populasi per tahun")
    # Use `spec` to drive code generation or template selection
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Literal
import re


# -----------------------------
# Constants / simple palettes
# -----------------------------

# A simple, readable color palette for group mapping (web hex colors).
# These mirror the spirit of Danim's group colors but expressed as hex.
DEFAULT_GROUP_COLOR_MAP: Dict[str, str] = {
    "AFRICA": "#F44336",  # RED
    "ASIA": "#4CAF50",  # GREEN
    "EUROPE": "#2196F3",  # BLUE
    "LATIN AMERICA AND THE CARIBBEAN": "#FFEB3B",  # YELLOW
    "OCEANIA": "#9C27B0",  # PURPLE
}

# Supported chart types for this module
ChartType = Literal["bubble", "distribution", "bar_race", "line", "unknown"]


# -----------------------------
# Dataclasses (Spec Schema)
# -----------------------------

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
    Axes configuration, compatible with both bubble and distribution visualizations.
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
    transform_ratio: float = 0.3  # fraction of (total_time - creation_time) used for bubble/data transforms
    lag_ratio: float = 0.3
    max_circles_per_batch: int = 60


@dataclass
class ChartSpec:
    """
    Unified chart spec used by the animation pipeline.

    Fields:
      - chart_type: "bubble" | "distribution" | "unknown"
      - data_binding: column bindings
      - axes: axis config
      - creation_mode: 1|2|3 (primarily for bubble charts; ignored for distribution)
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


# -----------------------------
# Inference helpers (regex)
# -----------------------------

_RE_BUBBLE = re.compile(
    r"(?:\bbubble\s*chart\b|\bbubblechart\b|\bbubble\b|\bgelembung\b|\bscatter\b|\bsebar\b)",
    re.IGNORECASE,
)
_RE_DISTRIBUTION = re.compile(
    r"(?:\bdistribution\b|\bdistribusi\b|\bhistogram\b|\bkde\b|\bdensity\b)",
    re.IGNORECASE,
)
_RE_LINE = re.compile(
    r"(?:\bline\s*chart\b|\bline\b|\btime\s*series\b|\bseries\b)",
    re.IGNORECASE,
)
_RE_MODE1 = re.compile(r"(?:\bmode\s*1\b|\boption\s*1\b|\bdirect(ly)?\b|\blangsung\b)", re.IGNORECASE)
_RE_MODE3 = re.compile(
    r"(?:\bmode\s*3\b|\boption\s*3\b|\b(group(ed)?|kelompok)\b|\bby\s*group\b)",
    re.IGNORECASE,
)
_RE_MODE2 = re.compile(r"(?:\bmode\s*2\b|\boption\s*2\b|\brandom\b)", re.IGNORECASE)

# Common label tokens (ID/EN) to set default axis labels if the prompt suggests domain context.
_RE_LIFE_EXPECTANCY = re.compile(r"(life\s*expectancy|umur\s*harapan\s*hidup|人均寿命)", re.IGNORECASE)
_RE_FERTILITY = re.compile(r"(fertilit(y|as)|生育率)", re.IGNORECASE)
_RE_POPULATION = re.compile(r"(population|populasi|人口)", re.IGNORECASE)
_RE_YEAR = re.compile(r"(year|tahun|年)", re.IGNORECASE)
_RE_REGION = re.compile(r"(region|wilayah|区域|area|benua)", re.IGNORECASE)


def normalize_chart_type(text: Optional[str]) -> ChartType:
    """
    Infer chart type from prompt text.
    """
    t = text or ""
    is_bubble = bool(_RE_BUBBLE.search(t))
    is_dist = bool(_RE_DISTRIBUTION.search(t))
    is_line = bool(_RE_LINE.search(t))
    # Prefer a single unambiguous match; otherwise return unknown and let dataset drive selection.
    if is_bubble and not (is_dist or is_line):
        return "bubble"
    if is_line and not (is_bubble or is_dist):
        return "line"
    if is_dist and not (is_bubble or is_line):
        return "distribution"
    return "unknown"


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


def infer_axis_labels(text: Optional[str]) -> tuple[Optional[str], Optional[str]]:
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
    Provide generic, reasonable default column names to guide the user/template.
    These are only placeholders; actual ingestion/validation will verify the dataset.
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
    if chart_type == "distribution":
        return DataBinding(
            value_col="value",
            time_col="time",
            group_col="group",
            entity_col="entity",
        )
    if chart_type == "bar_race":
        # Long-form preferred: time, category (as entity), value
        return DataBinding(
            value_col="value",
            time_col="time",
            group_col="group",
            entity_col="category",
        )
    if chart_type == "line":
        # Long-form preferred: time, series (as entity), value
        return DataBinding(
            value_col="value",
            time_col="time",
            group_col="series",
            entity_col="series",
        )
    # Unknown chart: set generic defaults to nudge user to map columns
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


def infer_spec_from_prompt(prompt: Optional[str]) -> ChartSpec:
    """
    Main entry: infer a minimal ChartSpec from the natural language prompt.
    - chart_type: bubble/distribution/unknown
    - creation_mode (bubble): 1/2/3
    - axes labels (optional)
    - style language (optional)
    - default bindings to guide downstream ingestion

    Note: This does not validate any dataset; it only generates a spec skeleton.
    """
    chart_type = normalize_chart_type(prompt)
    spec = build_default_spec(chart_type)

    # Infer creation mode for bubble charts
    if chart_type == "bubble":
        spec.creation_mode = infer_creation_mode(prompt)

    # Try lightweight axis labels (bubble)
    x_label, y_label = infer_axis_labels(prompt)
    if x_label:
        spec.axes.x_label = x_label
        # heuristic decimals for life expectancy
        spec.axes.x_decimals = 0
    if y_label:
        spec.axes.y_label = y_label
        spec.axes.y_decimals = 0

    # Parse explicit column binding overrides from prompt (e.g., x_col=lifeExp, y_col="fertility")
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


__all__ = [
    "ChartSpec",
    "DataBinding",
    "AxesSpec",
    "StyleSpec",
    "TimingSpec",
    "ChartType",
    "infer_spec_from_prompt",
    "normalize_chart_type",
    "infer_creation_mode",
    "default_binding_for_chart",
    "build_default_spec",
]
