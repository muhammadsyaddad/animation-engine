"""
Danim-style bubble chart code template generator (modern Manim).

This module generates a modern-Manim code string for a bubble chart animation
that closely resembles Danim's behavior (creation modes 1/2/3, group colors,
legend, and a time label). It avoids importing Danim directly and works with
Manim Community Edition (e.g., 0.18.x).

Usage:
    from agents.tools.specs import ChartSpec
    from agents.tools.danim_templates import generate_bubble_code

    spec = ...  # ChartSpec instance, with data_binding filled (x, y, r, time, group, entity/name)
    code_str = generate_bubble_code(spec, "/path/to/dataset.csv")
    # Feed code_str to the preview/render pipeline (expects class GenScene(Scene))

Notes:
- This function parses the CSV in-process and embeds preprocessed arrays in the
  generated code so the Manim runtime doesn't need to read files.
- Requires a dataset containing at least: x_col, y_col, r_col, time_col,
  and an entity/name column; group_col is recommended for coloring/legend.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

try:
    from agents.tools.specs import ChartSpec, DataBinding  # type: ignore
except Exception:
    # Minimal fallback annotations to avoid import-time errors in static analysis
    @dataclass
    class DataBinding:  # type: ignore
        x_col: Optional[str] = None
        y_col: Optional[str] = None
        r_col: Optional[str] = None
        value_col: Optional[str] = None
        time_col: Optional[str] = None
        group_col: Optional[str] = None

    @dataclass
    class ChartSpec:  # type: ignore
        chart_type: str = "bubble"
        data_binding: DataBinding = DataBinding()
        axes: object = None
        creation_mode: int = 2
        style: object = None
        timing: object = None


from typing import Sequence

def _detect_entity_col(headers: Sequence[str]) -> Optional[str]:
    """
    Best-effort detection of an entity/name identifier column in the dataset.
    Accepts any Sequence[str] for flexibility (list, tuple, etc.).
    """
    candidates = [
        "entity", "name", "country", "label", "id", "Entity", "Name", "Country", "Label", "ID"
    ]
    lower_headers = {h.lower(): h for h in headers}
    for cand in candidates:
        if cand.lower() in lower_headers:
            return lower_headers[cand.lower()]
    return None


def _read_float(row: Dict[str, str], key: str) -> Optional[float]:
    try:
        return float(row[key])
    except Exception:
        return None


def _read_time_token(row: Dict[str, str], key: str) -> str:
    val = (row.get(key) or "").strip()
    if not val:
        return ""
    # Prefer int-like formatting if possible
    try:
        num = float(val)
        if num.is_integer():
            return str(int(num))
        return str(num)
    except Exception:
        return val


def _parse_bubble_dataset(csv_path: str, binding: DataBinding) -> Tuple[
    List[str], List[str], Dict[str, str], Dict[str, Dict[str, Dict[str, float]]],
    Tuple[float, float, float, float], Tuple[float, float], List[str]
]:
    """
    Parse CSV into structures suitable for embedding into Manim code.

    Returns:
        times: sorted unique time tokens as strings
        entities: sorted unique entity identifiers
        group_of: mapping entity -> group (default "ALL" if group_col missing)
        data: dict time -> dict entity -> {"x": float, "y": float, "r": float}
        axis_ranges: (x_min, x_max, y_min, y_max)
        r_range: (r_min, r_max)
        groups_present: sorted unique group names present
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

        headers, rows = read_csv_rows(csv_path)

        x_col = binding.x_col or "x"
        y_col = binding.y_col or "y"
        r_col = binding.r_col or "r"
        t_col = binding.time_col or "time"
        g_col = binding.group_col or "group"
        e_col = _detect_entity_col(headers)
        if not e_col:
            raise ValueError(
                "Could not detect an entity/name column. Please include a column like "
                "'entity', 'name', 'country', 'label' in your dataset."
            )

        # Validate required columns
        needed = [x_col, y_col, r_col, t_col, e_col]
        missing = [c for c in needed if c not in headers]
        if missing:
            raise ValueError(f"Missing required columns in dataset: {missing}")

        times_set = set()
        entities_set = set()
        groups_present_set = set()
        group_of: Dict[str, str] = {}
        data: Dict[str, Dict[str, Dict[str, float]]] = {}

        x_vals: List[float] = []
        y_vals: List[float] = []
        r_vals: List[float] = []

        for row in reader:
            t = _read_time_token(row, t_col)
            if not t:
                continue
            x = _read_float(row, x_col)
            y = _read_float(row, y_col)
            r = _read_float(row, r_col)
            ent = (row.get(e_col) or "").strip()
            if not ent or x is None or y is None or r is None:
                continue

            grp = (row.get(g_col) or "ALL").strip()
            if not grp:
                grp = "ALL"

            # Accumulate
            times_set.add(t)
            entities_set.add(ent)
            groups_present_set.add(grp)
            group_of.setdefault(ent, grp)

            if t not in data:
                data[t] = {}
            data[t][ent] = {"x": float(x), "y": float(y), "r": float(r)}

            x_vals.append(float(x))
            y_vals.append(float(y))
            r_vals.append(float(r))

        if not times_set or not entities_set:
            raise ValueError("Dataset does not contain any valid records after parsing.")

        # Sort times (try numeric sort if possible)
        def _time_key(tok: str):
            try:
                return float(tok)
            except Exception:
                return tok

        times = sorted(times_set, key=_time_key)
        entities = sorted(entities_set)
        groups_present = sorted(groups_present_set)

        x_min, x_max = (min(x_vals), max(x_vals)) if x_vals else (0.0, 1.0)
        y_min, y_max = (min(y_vals), max(y_vals)) if y_vals else (0.0, 1.0)
        r_min, r_max = (min(r_vals), max(r_vals)) if r_vals else (1.0, 1.0)

        # Add small padding to axes ranges
        def pad_range(a: float, b: float, frac: float = 0.05) -> Tuple[float, float]:
            if a == b:
                return a - 1.0, b + 1.0
            span = (b - a)
            return a - span * frac, b + span * frac

        x_min, x_max = pad_range(x_min, x_max, 0.04)
        y_min, y_max = pad_range(y_min, y_max, 0.08)

        return (
            times,
            entities,
            group_of,
            data,
            (x_min, x_max, y_min, y_max),
            (r_min, r_max),
            groups_present,
        )


def _format_literal(obj) -> str:
    """
    Convert Python objects into a compact literal representation suitable for embedding into code.
    """
    # For floats, format to reasonable precision to keep code compact
    if isinstance(obj, float):
        return repr(round(obj, 6))
    if isinstance(obj, dict):
        items = ", ".join(f"{_format_literal(k)}: {_format_literal(v)}" for k, v in obj.items())
        return "{" + items + "}"
    if isinstance(obj, list):
        items = ", ".join(_format_literal(v) for v in obj)
        return "[" + items + "]"
    if isinstance(obj, tuple):
        items = ", ".join(_format_literal(v) for v in obj)
        return "(" + items + ")"
    if isinstance(obj, str):
        # Escape string safely
        return repr(obj)
    if isinstance(obj, bool):
        return "True" if obj else "False"
    if obj is None:
        return "None"
    return repr(obj)


def generate_bubble_code(spec: object, csv_path: str, use_modern: bool = True) -> str:
    """
    Generate a modern-Manim code string that defines class GenScene(Scene) for a
    Danim-style bubble chart animation.

    This function now delegates to the new modern template in
    agents.tools.templates.bubble_chart for better visual output with:
    - Modern color palette and theming
    - Properly formatted axis labels (K/M/B suffixes)
    - Smooth easing animations
    - Clean legend with rounded background
    - Optional entity labels on bubbles

    Args:
        spec: ChartSpec with data_binding filled (x,y,r,time, group optional).
        csv_path: Path to the dataset CSV.
        use_modern: If True (default), use the new modern template. Set False for legacy behavior.

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
    # Use the new modern bubble chart template by default
    if use_modern:
        from agents.tools.templates.bubble_chart import generate_bubble_chart
        return generate_bubble_chart(spec, csv_path, theme="youtube_dark")

    # Legacy implementation below (kept for backwards compatibility)
    # Parse dataset and compute derived metadata
    times, entities, group_of, data, (x_min, x_max, y_min, y_max), (r_min, r_max), groups_present = _parse_bubble_dataset(
        csv_path, spec.data_binding
    )

    # Decide axes ranges (auto/manual) with safe attribute guards
    axes_obj = getattr(spec, "axes", None)
    if axes_obj and getattr(axes_obj, "auto", True) is False:
        if getattr(axes_obj, "x_min", None) is not None:
            x_min = axes_obj.x_min
        if getattr(axes_obj, "x_max", None) is not None:
            x_max = axes_obj.x_max
        if getattr(axes_obj, "y_min", None) is not None:
            y_min = axes_obj.y_min
        if getattr(axes_obj, "y_max", None) is not None:
            y_max = axes_obj.y_max

    # Axis labels / decimals
    x_label = getattr(spec.axes, "x_label", None) if getattr(spec, "axes", None) else None
    y_label = getattr(spec.axes, "y_label", None) if getattr(spec, "axes", None) else None
    x_decimals = getattr(spec.axes, "x_decimals", 0) if getattr(spec, "axes", None) else 0
    y_decimals = getattr(spec.axes, "y_decimals", 0) if getattr(spec, "axes", None) else 0
    show_numbers = getattr(spec.axes, "show_numbers", True) if getattr(spec, "axes", None) else True
    show_axis_labels = getattr(spec.axes, "show_axis_labels", True) if getattr(spec, "axes", None) else True

    # Style
    fill_opacity = getattr(spec.style, "fill_opacity", 0.7) if getattr(spec, "style", None) else 0.7
    stroke_width = getattr(spec.style, "stroke_width", 1.5) if getattr(spec, "style", None) else 1.5
    label_language = getattr(spec.style, "label_language", None) if getattr(spec, "style", None) else None
    show_legend = getattr(spec.style, "show_legend", True) if getattr(spec, "style", None) else True
    color_map = getattr(spec.style, "color_map", {}) if getattr(spec, "style", None) else {}

    # Build a final color map that includes any unseen groups with fallback palette
    fallback_palette = [
        "#F44336", "#4CAF50", "#2196F3", "#FFEB3B", "#9C27B0",
        "#FF9800", "#009688", "#3F51B5", "#E91E63", "#8BC34A",
    ]
    final_color_map: Dict[str, str] = {}
    fallback_idx = 0
    for g in groups_present:
        if g in color_map and color_map[g]:
            final_color_map[g] = color_map[g]
        else:
            final_color_map[g] = fallback_palette[fallback_idx % len(fallback_palette)]
            fallback_idx += 1

    # Timing
    total_time = getattr(spec.timing, "total_time", 30.0) if getattr(spec, "timing", None) else 30.0
    creation_time = getattr(spec.timing, "creation_time", 2.0) if getattr(spec, "timing", None) else 2.0
    transform_ratio = getattr(spec.timing, "transform_ratio", 0.3) if getattr(spec, "timing", None) else 0.3
    lag_ratio = getattr(spec.timing, "lag_ratio", 0.3) if getattr(spec, "timing", None) else 0.3
    max_circles_per_batch = getattr(spec.timing, "max_circles_per_batch", 60) if getattr(spec, "timing", None) else 60

    # Creation mode
    creation_mode = int(getattr(spec, "creation_mode", 2) or 2)
    if creation_mode not in (1, 2, 3):
        creation_mode = 2

    # Derived times for per-step transforms
    steps = max(1, len(times) - 1)
    transform_total_time = max(0.5, total_time - creation_time)
    per_step_time = transform_total_time / steps

    # Bubble radius normalization (Danim uses area-proportional approach; we approximate via sqrt scaling)
    r_min = float(r_min)
    r_max = float(r_max)
    if r_min <= 0:
        r_min = 1e-6
    if r_max <= 0:
        r_max = r_min + 1.0
    radius_min = 0.08
    radius_max = 0.60

    # Embed literals
    lit_times = _format_literal(times)
    lit_entities = _format_literal(entities)
    lit_group_of = _format_literal(group_of)
    lit_data = _format_literal(data)
    lit_color_map = _format_literal(final_color_map)

    code = f'''
from manim import *
import math

# Embedded dataset (parsed server-side)
TIMES = {lit_times}
ENTITIES = {lit_entities}
GROUP_OF = {lit_group_of}
DATA = {lit_data}  # DATA[time][entity] = {{ "x": float, "y": float, "r": float }}
GROUP_COLOR_MAP = {lit_color_map}

# Axis configuration (auto/manual resolved server-side)
X_MIN, X_MAX = {x_min}, {x_max}
Y_MIN, Y_MAX = {y_min}, {y_max}
SHOW_NUMBERS = {show_numbers}
SHOW_AXIS_LABELS = {show_axis_labels}
X_LABEL = {repr(x_label) if x_label is not None else "None"}
Y_LABEL = {repr(y_label) if y_label is not None else "None"}
X_DECIMALS = {x_decimals}
Y_DECIMALS = {y_decimals}

# Visual style
FILL_OPACITY = {fill_opacity}
STROKE_WIDTH = {stroke_width}
SHOW_LEGEND = {show_legend}

# Timing
CREATION_TIME = {creation_time}
PER_STEP_TIME = {per_step_time}
LAG_RATIO = {lag_ratio}
MAX_CIRCLES_PER_BATCH = {max_circles_per_batch}
CREATION_MODE = {creation_mode}  # 1: all at once, 2: random batch, 3: by group

# Bubble radius normalization (sqrt-area scaling)
R_MIN = {r_min}
R_MAX = {r_max}
RADIUS_MIN = {radius_min}
RADIUS_MAX = {radius_max}


def compute_radius(rv: float) -> float:
    rmin = max(R_MIN, 1e-9)
    rmax = max(R_MAX, rmin + 1e-9)
    if rmax == rmin:
        return 0.5 * (RADIUS_MIN + RADIUS_MAX)
    # sqrt-area normalization
    sv = math.sqrt(max(rv, 0.0))
    smin = math.sqrt(rmin)
    smax = math.sqrt(rmax)
    t = 0.0 if (smax - smin) <= 1e-12 else (sv - smin) / (smax - smin)
    t = max(0.0, min(1.0, t))
    return RADIUS_MIN + t * (RADIUS_MAX - RADIUS_MIN)


def make_axes() -> Axes:
    x_step = (X_MAX - X_MIN) / 10.0 if X_MAX > X_MIN else 1.0
    y_step = (Y_MAX - Y_MIN) / 10.0 if Y_MAX > Y_MIN else 1.0
    axes = Axes(
        x_range=[X_MIN, X_MAX, x_step],
        y_range=[Y_MIN, Y_MAX, y_step],
        tips=False,
    )
    # Numbers appear if SHOW_NUMBERS; in Manim, Axes tick numbers appear via labels arguments,
    # but for simplicity we rely on default ticks and show/hide axis labels only.
    if SHOW_AXIS_LABELS:
        x_lab = X_LABEL if X_LABEL else "X"
        y_lab = Y_LABEL if Y_LABEL else "Y"
        x_label = Text(x_lab).scale(0.5).next_to(axes.x_axis, DOWN, buff=0.3)
        y_label = Text(y_lab).scale(0.5).next_to(axes.y_axis, LEFT, buff=0.3)
        axes.add(x_label, y_label)
    return axes


def color_for_entity(ent: str) -> Color:
    grp = GROUP_OF.get(ent, "ALL")
    hex_color = GROUP_COLOR_MAP.get(grp, "#999999")
    try:
        return Color(hex_color)
    except Exception:
        return WHITE


def make_legend(groups: list[str]) -> VGroup:
    items = VGroup()
    # Position legend at top-right
    base = ORIGIN
    for i, g in enumerate(groups):
        swatch = Square(side_length=0.25).set_fill(Color(GROUP_COLOR_MAP.get(g, "#999999")), opacity=1.0)
        swatch.set_stroke(width=0)
        label = Text(str(g), font_size=22)
        entry = VGroup(swatch, label)
        label.next_to(swatch, RIGHT, buff=0.2)
        entry.arrange(RIGHT, buff=0.25)
        items.add(entry)
    items.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
    items.to_corner(UR, buff=0.6)
    # Add a subtle frame
    frame = SurroundingRectangle(items, buff=0.25, corner_radius=0.1, color=GREY_B)
    return VGroup(frame, items)


class GenScene(Scene):
    def construct(self):
        # Axes
        axes = make_axes()
        self.play(Create(axes), run_time=0.8)

        # Time label
        current_time = TIMES[0] if TIMES else ""
        time_label = Text(str(current_time), font_size=36, color=PURPLE_E)
        time_label.to_corner(UL, buff=0.6)
        self.add(time_label)

        # Legend
        groups_present = sorted(set(GROUP_OF.values()))
        legend = None
        if SHOW_LEGEND and groups_present:
            legend = make_legend(groups_present)
            self.play(FadeIn(legend), run_time=0.6)

        # Prepare initial circles at t0
        t0 = TIMES[0]
        circles = {{}}
        for ent in ENTITIES:
            rec = DATA.get(t0, {{}}).get(ent)
            if not rec:
                # entity missing at t0, fallback to some neutral defaults
                x0, y0, r0 = (0.0, 0.0, 1.0)
            else:
                x0, y0, r0 = rec["x"], rec["y"], rec["r"]

            p0 = axes.coords_to_point(x0, y0)
            rad = compute_radius(r0)
            c = Circle(radius=rad)
            c.set_fill(color_for_entity(ent), opacity=FILL_OPACITY)
            c.set_stroke(color=color_for_entity(ent), width=STROKE_WIDTH, opacity=1.0)
            c.move_to(p0)
            circles[ent] = c

        # Creation modes
        if CREATION_MODE == 1:
            # Directly show everything
            self.play(*[GrowFromCenter(circles[e]) for e in ENTITIES], run_time=CREATION_TIME, lag_ratio=LAG_RATIO)
        elif CREATION_MODE == 2:
            # Random batch creation then transfer to exact position (approximation)
            import random
            ents = ENTITIES.copy()
            random.shuffle(ents)
            # Appear from a corner
            appear_pos = axes.coords_to_point(X_MAX, Y_MAX)
            for e in ents:
                circles[e].move_to(appear_pos)
            # Add all but invisible
            for e in ents:
                self.add(circles[e])
            # Grow in batches
            for i in range(0, len(ents), MAX_CIRCLES_PER_BATCH):
                batch = ents[i:i+MAX_CIRCLES_PER_BATCH]
                self.play(*[GrowFromCenter(circles[e]) for e in batch], run_time=CREATION_TIME * 0.6, lag_ratio=LAG_RATIO)
                # Transfer to true positions
                self.play(*[circles[e].animate.move_to(axes.coords_to_point(
                    DATA.get(t0, {{}}).get(e, {{}}).get("x", 0.0),
                    DATA.get(t0, {{}}).get(e, {{}}).get("y", 0.0),
                )) for e in batch], run_time=CREATION_TIME * 0.4, lag_ratio=LAG_RATIO)
        else:
            # CREATION_MODE == 3: by group
            # Appear group-by-group
            idx_map = {{}}
            for g in groups_present:
                members = [e for e in ENTITIES if GROUP_OF.get(e, "ALL") == g]
                # place at a near-corner position first
                appear_pos = axes.coords_to_point(X_MAX, Y_MAX)
                for e in members:
                    circles[e].move_to(appear_pos)
                # Add all first
                for e in members:
                    self.add(circles[e])
                # Indicate legend group if present
                if legend:
                    try:
                        self.play(Indicate(legend[1].submobjects[groups_present.index(g)]), run_time=0.4)
                    except Exception:
                        pass
                # Grow and transfer
                self.play(*[GrowFromCenter(circles[e]) for e in members], run_time=CREATION_TIME * 0.6, lag_ratio=LAG_RATIO)
                self.play(*[circles[e].animate.move_to(axes.coords_to_point(
                    DATA.get(t0, {{}}).get(e, {{}}).get("x", 0.0),
                    DATA.get(t0, {{}}).get(e, {{}}).get("y", 0.0),
                )) for e in members], run_time=CREATION_TIME * 0.4, lag_ratio=LAG_RATIO)

        # Ensure all circles are in the scene (for mode 1 path)
        if CREATION_MODE == 1:
            self.add(*[circles[e] for e in ENTITIES])

        # Update over time steps
        for ti in range(1, len(TIMES)):
            t = TIMES[ti]
            # Update time label
            new_label = Text(str(t), font_size=36, color=PURPLE_E).to_corner(UL, buff=0.6)
            self.play(Transform(time_label, new_label), run_time=PER_STEP_TIME * 0.25)

            # Compute animations for all entities present at time t
            anims = []
            for ent in ENTITIES:
                rec = DATA.get(t, {{}}).get(ent)
                if not rec:
                    continue
                x1, y1, r1 = rec["x"], rec["y"], rec["r"]
                p1 = axes.coords_to_point(x1, y1)
                new_radius = compute_radius(r1)
                # Animate move + size
                anims.append(circles[ent].animate.move_to(p1))
                # Set diameter via width
                anims.append(circles[ent].animate.set(width=2.0 * new_radius))
            if anims:
                self.play(*anims, run_time=PER_STEP_TIME * 0.75, lag_ratio=LAG_RATIO)

        self.wait(0.5)
'''
    return code.strip()

def generate_distribution_code(spec: object, csv_path: str) -> str:
    """
    Generate a modern-Manim code string that defines class GenScene(Scene) for a
    distribution (histogram) animation over time.

    This function now delegates to the new modern template in
    agents.tools.templates.distribution for better visual output with:
    - Properly formatted axis labels (K/M/B suffixes)
    - Smart bin labeling that doesn't overlap
    - Rotated labels to prevent collision
    - Modern color palette and styling

    Args:
        spec: ChartSpec with data_binding filled (value,time[,group/entity optional]).
        csv_path: Path to the dataset CSV.

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
    # Use the new modern distribution template
    from agents.tools.templates.distribution import generate_distribution
    return generate_distribution(spec, csv_path, theme="youtube_dark")

def generate_bar_race_code(spec: object, csv_path: str) -> str:
    """
    Generate 'True' Bar Chart Race code where bars actually swap positions via ranking logic.

    This function delegates to the story-driven bar race template with:
    - Story-driven narrative structure (intro, reveal, race, conclusion)
    - Auto-detected insights (leader changes, big jumps)
    - Modern color palette
    - Smooth easing animations
    - Proper value formatting (K/M/B suffixes)
    - Rounded corners and polished styling
    - Configurable narrative styles

    Args:
        spec: ChartSpec with data_binding filled.
        csv_path: Path to the dataset CSV.

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
    from agents.tools.templates.bar_race import generate_bar_race
    return generate_bar_race(
        spec,
        csv_path,
        theme="youtube_dark",
        include_intro=True,
        include_conclusion=True,
        auto_highlights=True,
    )

def generate_line_evolution_code(spec: object, csv_path: str) -> str:
    """
    Generate a 'Dynamic Line Evolution' chart.
    Perfect for single-variable time series (Stock price, Temperature, etc.).

    This function now delegates to the new modern template in
    agents.tools.templates.line_evolution for better visual output with:
    - Glowing tracking dot
    - Smooth curve drawing with area fill
    - Animated value counter
    - Modern color palette and styling

    Args:
        spec: ChartSpec with data_binding filled.
        csv_path: Path to the dataset CSV.

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
    # Use the new modern line evolution template
    from agents.tools.templates.line_evolution import generate_line_evolution
    return generate_line_evolution(spec, csv_path, theme="youtube_dark")


def generate_bento_grid_code(spec: object, csv_path: str, use_modern: bool = True) -> str:
    """
    Generate a 'Bento Grid' KPI Dashboard.
    Best for: Snapshot data, summary statistics, or small datasets (< 10 items).

    This function now delegates to the new modern template in
    agents.tools.templates.bento_grid for better visual output with:
    - Glassmorphism card design with subtle gradients
    - Animated counting numbers with K/M/B formatting
    - Optional change indicators (up/down arrows with percentages)
    - Flexible grid layouts (auto or manual)
    - Modern color palette and theming

    Args:
        spec: ChartSpec with data_binding filled.
        csv_path: Path to the dataset CSV.
        use_modern: If True (default), use the new modern template. Set False for legacy behavior.

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
    # Use the new modern bento grid template by default
    if use_modern:
        from agents.tools.templates.bento_grid import generate_bento_grid
        return generate_bento_grid(spec, csv_path, theme="youtube_dark")

    # Legacy implementation below (kept for backwards compatibility)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    import csv
    import math

    # --- 1. DATA PARSING ---
    # Kita butuh pasangan: (Label, Value)
    # Bisa dari kolom: (Category, Value)

    label_col = getattr(getattr(spec, "data_binding", None), "entity_col", None) or "name"
    value_col = getattr(getattr(spec, "data_binding", None), "value_col", None) or "value"

    def _resolve_headers(headers, target, candidates):
        if target in headers: return target
        lower = {h.lower(): h for h in headers}
        for c in candidates:
            if c in headers: return c
            if c.lower() in lower: return lower[c.lower()]
        return target

    items = [] # List of {'label': str, 'value': float}

    headers, rows = read_csv_rows(csv_path)

    # Smart Column Detection
    label_col = _resolve_headers(headers, label_col, ["metric", "kpi", "category", "item", "name", "title", "label"])
    value_col = _resolve_headers(headers, value_col, ["value", "amount", "total", "count", "number", "score"])

    for row in rows:
        lbl = (row.get(label_col) or "").strip()
        val_str = (row.get(value_col) or "").strip()

        if not lbl or not val_str: continue
        try:
            # Clean currency symbols or commas if simple
            clean_val = val_str.replace(",", "").replace("$", "").replace("%", "")
            val = float(clean_val)
            items.append({"label": lbl, "value": val})
        except:
            continue

    # --- 2. SAFETY LIMITS ---
    # Bento Grid paling bagus max 9 items (3x3). Lebih dari itu jadi kekecilan.
    # Kita ambil top 9 items aja kalau kebanyakan.
    if not items:
        raise ValueError("No valid KPI data found.")

    items = items[:9]

    # --- 3. LAYOUT CALCULATION ---
    n = len(items)
    # Tentukan grid cols ideal
    if n == 1: cols = 1
    elif n <= 4: cols = 2
    else: cols = 3

    # --- 4. VISUAL CONFIG ---
    # Palette Warna Modern (Dark UI friendly)
    colors = [
        "#4CC9F0", "#4895EF", "#4361EE", "#3F37C9",
        "#3A0CA3", "#7209B7", "#F72585", "#FF4D6D", "#FF758F"
    ]

    # Format literal
    lit_items = _format_literal(items)
    lit_colors = _format_literal(colors)

    code = f'''
from manim import *

DATA_ITEMS = {lit_items}
COLORS = {lit_colors}
COLS = {cols}

class GenScene(Scene):
    def construct(self):
        # Container Group
        cards = VGroup()

        # Create Card Objects
        trackers = [] # Simpan tracker angka untuk animasi nanti
        decimal_mobs = [] # Simpan object DecimalNumber

        for i, item in enumerate(DATA_ITEMS):
            label_text = item["label"]
            target_val = item["value"]
            color = COLORS[i % len(COLORS)]

            # 1. The Card Shape (Bento Box)
            # Ukuran dinamis? Kita pakai standard dulu, nanti arrange grid yg ngatur.
            card_width = 4.0
            card_height = 2.5

            bg = RoundedRectangle(corner_radius=0.2, width=card_width, height=card_height)
            bg.set_fill(color, opacity=0.1) # Glassmorphism style (low opacity)
            bg.set_stroke(color, width=2)

            # 2. The Label (Top, Smaller, Uppercase)
            lbl = Text(str(label_text).upper(), font_size=20, weight=BOLD, color=GREY_B)
            # Posisikan di bagian atas dalam kartu
            lbl.move_to(bg.get_top() + DOWN * 0.5)

            # 3. The Value (Center, Huge)
            # Kita pakai DecimalNumber untuk animasi counting
            val_num = DecimalNumber(0, num_decimal_places=0, font_size=60, color=WHITE)
            if abs(target_val) < 10 and isinstance(target_val, float):
                 val_num = DecimalNumber(0, num_decimal_places=2, font_size=60, color=WHITE)

            val_num.move_to(bg.get_center())

            # Auto-scale if number is too wide (e.g. billions)
            # Batasi lebar angka maks 80% lebar kartu
            max_width = card_width * 0.8
            if val_num.width > max_width:
                 val_num.scale_to_fit_width(max_width)

            # Grouping
            card_group = VGroup(bg, lbl, val_num)
            cards.add(card_group)

            # Setup Animation Trackers
            tracker = ValueTracker(0)
            trackers.append((tracker, target_val))
            decimal_mobs.append(val_num)

            # Updater: Hubungkan DecimalNumber dengan Tracker
            # Kita butuh closure trick python biar variable 't' dan 'v' ter-bind dengan benar
            def get_updater(mob, t):
                return lambda m: m.set_value(t.get_value())

            val_num.add_updater(get_updater(val_num, tracker))

        # Arrange Grid
        # arrange_in_grid otomatis membagi baris/kolom
        cards.arrange_in_grid(cols=COLS, buff=0.5)

        # Scale grid to fit screen if necessary
        if cards.width > config.frame_width - 1:
            cards.scale_to_fit_width(config.frame_width - 1)
        if cards.height > config.frame_height - 1:
            cards.scale_to_fit_height(config.frame_height - 1)

        cards.move_to(ORIGIN)

        # --- ANIMATION SEQUENCE ---

        # 1. Intro: Cards Fade In + Scale Up
        self.play(
            LaggedStart(
                *[FadeIn(c, shift=UP*0.5, scale=0.9) for c in cards],
                lag_ratio=0.1
            ),
            run_time=1.5
        )

        # 2. Counting Animation (Parallel)
        # Semua angka naik bareng-bareng dari 0 ke Target Value
        anims = []
        for tracker, target in trackers:
            anims.append(tracker.animate.set_value(target))

        self.play(*anims, run_time=2.0, rate_func=ease_out_circ)

        # 3. Highlight / Shimmer (Optional Polish)
        # Flash border card random untuk memberi kesan "Live Data"
        if len(cards) > 0:
             self.play(Indicate(cards[0][0], color=WHITE), run_time=0.5)

        self.wait(2)

'''
    return code.strip()


def generate_count_bar_code(spec: object, csv_path: str, count_column: str = None, top_n: int = 15) -> str:
    """
    Generate a 'Count Bar Chart' for categorical-only datasets.

    Converts categorical data to counts and creates an animated horizontal bar chart
    with staggered growth animation. Perfect for datasets that have no numeric columns
    but contain categorical values that can be counted.

    This function delegates to the count_bar template with:
    - Horizontal bar chart with animated growth
    - Staggered entrance animation for visual interest
    - Value labels at the end of each bar
    - Clean, modern styling using the current color palette
    - Auto-sorted by count (descending) for visual hierarchy

    Args:
        spec: ChartSpec with data_binding filled.
        csv_path: Path to the dataset CSV.
        count_column: Column to count occurrences of (None = auto-detect).
        top_n: Maximum number of categories to show (default 15).

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
    from agents.tools.templates.count_bar import generate_count_bar
    return generate_count_bar(
        spec,
        csv_path,
        count_column=count_column,
        top_n=top_n,
        theme="youtube_dark",
        include_intro=True,
        include_conclusion=True,
    )


def generate_single_numeric_code(
    spec: object,
    csv_path: str,
    category_column: str = None,
    value_column: str = None,
    top_n: int = 15,
    sort_descending: bool = True,
) -> str:
    """
    Generate a 'Single Numeric Bar Chart' for datasets with one numeric column.

    Creates an animated horizontal bar chart showing actual values per category.
    Perfect for datasets with one categorical column and one numeric column
    (e.g., revenue by product, population by country).

    This function delegates to the single_numeric template with:
    - Horizontal bar chart with animated growth
    - Staggered entrance animation for visual interest
    - Value labels at the end of each bar with K/M/B formatting
    - Clean, modern styling using the current color palette
    - Optional sorting by value (descending)

    Args:
        spec: ChartSpec with data_binding filled.
        csv_path: Path to the dataset CSV.
        category_column: Column for categories (None = auto-detect).
        value_column: Column for numeric values (None = auto-detect).
        top_n: Maximum number of categories to show (default 15).
        sort_descending: Whether to sort by value descending (default True).

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
    from agents.tools.templates.single_numeric import generate_single_numeric
    return generate_single_numeric(
        spec,
        csv_path,
        category_column=category_column,
        value_column=value_column,
        top_n=top_n,
        sort_descending=sort_descending,
        theme="youtube_dark",
        include_intro=True,
        include_conclusion=True,
    )
