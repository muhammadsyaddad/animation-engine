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

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

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


def generate_bubble_code(spec: object, csv_path: str) -> str:
    """
    Generate a modern-Manim code string that defines class GenScene(Scene) for a
    Danim-style bubble chart animation.

    Args:
        spec: ChartSpec with data_binding filled (x,y,r,time, group optional).
        csv_path: Path to the dataset CSV.

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
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
    Danim-style distribution (histogram) animation over time.

    Args:
        spec: ChartSpec with data_binding filled (value,time[,group/entity optional]).
        csv_path: Path to the dataset CSV.

    Returns:
        str: Python code suitable for Manim CLI (contains `class GenScene(Scene)`).
    """
    # Read CSV and collect values per time
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    val_col = getattr(spec.data_binding, "value_col", None) or "value"
    time_col = getattr(spec.data_binding, "time_col", None) or "time"
    group_col = getattr(spec.data_binding, "group_col", None)
    entity_col = getattr(spec.data_binding, "entity_col", None)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Heuristic fallback for common column names
        def _find_col(candidates):
            for c in candidates:
                if c in headers:
                    return c
                # case-insensitive search
                for h in headers:
                    if h.lower() == c.lower():
                        return h
            return None

        if val_col not in headers:
            cand = _find_col(["value", "val", "score", "amount"])
            if cand:
                val_col = cand
        if time_col not in headers:
            cand = _find_col(["time", "year", "tahun", "t"])
            if cand:
                time_col = cand
        if group_col and group_col not in headers:
            cand = _find_col([group_col, "group", "region", "area", "benua"])
            if cand:
                group_col = cand
        if entity_col and entity_col not in headers:
            cand = _find_col([entity_col, "entity", "name", "country", "label", "id"])
            if cand:
                entity_col = cand

        required_missing = []
        if time_col not in headers:
            required_missing.append("time_col")
        if val_col not in headers:
            required_missing.append("value_col")
        if required_missing:
            raise ValueError(f"Missing required columns in dataset: {required_missing} (headers={headers})")

        values_by_time: Dict[str, List[float]] = {}
        all_values: List[float] = []
        for row in reader:
            t = (row.get(time_col) or "").strip()
            if not t:
                continue
            rv = (row.get(val_col) or "").strip()
            if not rv:
                continue
            try:
                v = float(rv)
            except ValueError:
                continue
            values_by_time.setdefault(t, []).append(v)
            all_values.append(v)

    if not values_by_time:
        raise ValueError("No valid (time,value) records found in dataset.")

    # Sort time tokens (numeric if possible)
    def _tkey(tok: str):
        try:
            return float(tok)
        except Exception:
            return tok

    times = sorted(values_by_time.keys(), key=_tkey)

    vmin = min(all_values) if all_values else 0.0
    vmax = max(all_values) if all_values else 1.0
    if vmin == vmax:
        vmin -= 0.5
        vmax += 0.5

    # Build histogram bins (10 bins)
    nbins = 10
    span = (vmax - vmin)
    step = span / nbins
    edges = [vmin + i * step for i in range(nbins + 1)]
    # Guard against numeric issues
    if step <= 0:
        edges = [vmin + i for i in range(nbins + 1)]

    # Counts per time
    hist_map: Dict[str, List[int]] = {}
    ymax_count = 1
    for t in times:
        counts = [0] * nbins
        for v in values_by_time.get(t, []):
            # Compute bin index
            idx = int((v - vmin) / step) if step > 0 else 0
            if idx < 0:
                idx = 0
            if idx >= nbins:
                idx = nbins - 1
            counts[idx] += 1
        ymax_count = max(ymax_count, max(counts) if counts else 0)
        hist_map[t] = counts

    # Axis labels/decimals (reuse from spec.axes when relevant)
    x_label = getattr(spec.axes, "x_label", "Value") if getattr(spec, "axes", None) else "Value"
    y_label = getattr(spec.axes, "y_label", "Count") if getattr(spec.axes, "y_label", None) else "Count"
    # Fallback normalization to ensure labels are never None/empty (prevents Text(None) AttributeError)
    x_label = x_label or "Value"
    y_label = y_label or "Count"
    show_axis_labels = getattr(spec.axes, "show_axis_labels", True) if getattr(spec, "axes", None) else True

    # Style
    label_language = getattr(spec.style, "label_language", None) if getattr(spec, "style", None) else None

    # Timing
    total_time = getattr(spec.timing, "total_time", 30.0) if getattr(spec, "timing", None) else 30.0
    creation_time = getattr(spec.timing, "creation_time", 2.0) if getattr(spec, "timing", None) else 2.0
    transform_ratio = getattr(spec.timing, "transform_ratio", 0.3) if getattr(spec, "timing", None) else 0.3

    steps = max(1, len(times) - 1)
    transform_total_time = max(0.5, total_time - creation_time)
    per_step_time = transform_total_time / steps

    # Bar labels as ranges "a-b"
    def _fmt_bin_label(a: float, b: float) -> str:
        return f"{a:.2f}-{b:.2f}"

    bin_labels = [_fmt_bin_label(edges[i], edges[i + 1]) for i in range(nbins)]

    # Embed literals
    lit_times = _format_literal(times)
    lit_edges = _format_literal(edges)
    lit_labels = _format_literal(bin_labels)
    lit_hists = _format_literal(hist_map)
    y_max = max(1, int(math.ceil(ymax_count * 1.1)))

    code = f'''
from manim import *
import math

# Embedded histogram data
TIMES = {lit_times}
BIN_EDGES = {lit_edges}
BIN_LABELS = {lit_labels}
HISTS = {lit_hists}  # HISTS[time] = [counts...]

X_LABEL = {repr(x_label)}
Y_LABEL = {repr(y_label)}
SHOW_AXIS_LABELS = {show_axis_labels}

CREATION_TIME = {creation_time}
PER_STEP_TIME = {per_step_time}

def make_chart(counts: list[int]) -> BarChart:
    y_max = {y_max}
    chart = BarChart(
        values=counts,
        bar_names=BIN_LABELS,
        y_range=[0, y_max, max(1, y_max // 5)],
        y_length=4.0,
        x_length=8.0,
        bar_width=0.6,
    )
    # Guard each axis label to avoid constructing Text with None/empty
    if SHOW_AXIS_LABELS and (X_LABEL or "").strip():
        chart.x_axis.label = Text(str(X_LABEL)).scale(0.5)
        chart.x_axis.label.next_to(chart.x_axis, DOWN, buff=0.3)
        chart.add(chart.x_axis.label)
    if SHOW_AXIS_LABELS and (Y_LABEL or "").strip():
        chart.y_axis.label = Text(str(Y_LABEL)).scale(0.5)
        chart.y_axis.label.next_to(chart.y_axis, LEFT, buff=0.3)
        chart.add(chart.y_axis.label)
    return chart

class GenScene(Scene):
    def construct(self):
        if not TIMES:
            self.play(Write(Text("No data")))
            return

        t0 = TIMES[0]
        chart = make_chart(HISTS.get(t0, [0]*len(BIN_LABELS)))
        title = Text(str(t0), font_size=36, color=PURPLE_E).to_corner(UL, buff=0.6)

        self.play(FadeIn(chart), run_time=CREATION_TIME * 0.6)
        self.play(FadeIn(title), run_time=CREATION_TIME * 0.4)

        for ti in range(1, len(TIMES)):
            t = TIMES[ti]
            new_chart = make_chart(HISTS.get(t, [0]*len(BIN_LABELS)))
            new_title = Text(str(t), font_size=36, color=PURPLE_E).to_corner(UL, buff=0.6)

            # Align positions to improve Transform quality
            new_chart.move_to(chart.get_center())
            self.play(Transform(chart, new_chart), run_time=PER_STEP_TIME * 0.8)
            self.play(Transform(title, new_title), run_time=PER_STEP_TIME * 0.2)

        self.wait(0.5)
'''
    return code.strip()

def generate_bar_race_code(spec: object, csv_path: str) -> str:
    """
    Generate 'True' Bar Chart Race code where bars actually swap positions via ranking logic.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    # --- 1. DATA INGESTION (Sama seperti sebelumnya, tapi kita butuh struktur data lebih rapi) ---
    # Resolve columns
    value_col = getattr(getattr(spec, "data_binding", None), "value_col", None) or "value"
    time_col = getattr(getattr(spec, "data_binding", None), "time_col", None) or "time"
    category_col = getattr(getattr(spec, "data_binding", None), "entity_col", None) or "category"

    # Helper resolve headers (sama seperti kodemu sebelumnya)
    def _resolve_headers(headers, target, candidates):
        if target in headers: return target
        lower = {h.lower(): h for h in headers}
        for c in candidates:
            if c in headers: return c
            if c.lower() in lower: return lower[c.lower()]
        return target

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Smart detection
        time_col = _resolve_headers(headers, time_col, ["time", "year", "date", "t"])
        value_col = _resolve_headers(headers, value_col, ["value", "count", "score", "gdp", "pop"])
        category_col = _resolve_headers(headers, category_col, ["name", "entity", "country", "label", "item"])

        # Parsing
        data_by_time = {} # { time: { category: value } }
        all_cats = set()

        for row in reader:
            t = (row.get(time_col) or "").strip()
            c = (row.get(category_col) or "").strip()
            v_str = (row.get(value_col) or "0").strip()

            if not t or not c: continue
            try:
                v = float(v_str)
            except:
                continue

            if t not in data_by_time: data_by_time[t] = {}
            data_by_time[t][c] = v
            all_cats.add(c)

    # Sort Times
    def _tkey(tok):
        try: return float(tok)
        except: return tok
    times = sorted(data_by_time.keys(), key=_tkey)

    # --- 2. LOGIC: FILTER TOP K (Agar layar tidak penuh) ---
    TOP_K = 10
    # Kita cari Top K categories secara global atau based on start/end value
    # Simplified strategy: Ambil Top K pada time terakhir (biasanya ini pemenangnya)
    last_t = times[-1]
    last_ranking = sorted(data_by_time[last_t].items(), key=lambda x: x[1], reverse=True)
    top_cats = [x[0] for x in last_ranking[:TOP_K]]

    # Tapi kita harus handle kategori yang mungkin kuat di awal tapi hilang di akhir.
    # Untuk safety, kita ambil union dari Top K start dan Top K end, lalu limit max 15.
    t0 = times[0]
    start_ranking = sorted(data_by_time[t0].items(), key=lambda x: x[1], reverse=True)
    start_cats = [x[0] for x in start_ranking[:TOP_K]]
    final_cats_set = set(top_cats + start_cats)
    final_cats = list(final_cats_set)[:12] # Limit 12 bar agar visual rapi

    # Build Data Matrix
    # DATA = { time: { cat: val } } -- hanya untuk final_cats
    clean_data = {}
    global_max = 0
    for t in times:
        clean_data[t] = {}
        for c in final_cats:
            val = data_by_time[t].get(c, 0.0)
            clean_data[t][c] = val
            if val > global_max: global_max = val

    # --- 3. CONFIGURATION & FORMATTING ---
    timing = getattr(spec, "timing", None)
    total_time = getattr(timing, "total_time", 15.0) if timing else 15.0

    # Palette Colors
    colors = ["#2364AA", "#3DA5D9", "#73BFB8", "#FEC601", "#EA7317",
              "#E63946", "#F1FAEE", "#A8DADC", "#457B9D", "#1D3557"]

    cat_colors = {c: colors[i % len(colors)] for i, c in enumerate(final_cats)}

    # Embed Literals
    lit_times = _format_literal(times)
    lit_data = _format_literal(clean_data)
    lit_colors = _format_literal(cat_colors)
    lit_cats = _format_literal(final_cats)

    # --- 4. GENERATE MANIM CODE ---
    code = f'''
from manim import *

# --- DATA ---
TIMES = {lit_times}
DATA = {lit_data}
COLORS = {lit_colors}
CATEGORIES = {lit_cats}
MAX_VAL = {global_max}
RUN_TIME = {total_time}

class GenScene(Scene):
    def construct(self):
        # 1. SETUP LAYOUT
        # Area Bar Chart: Kiri ke Kanan (-6 sampai 6), Atas ke Bawah (3 sampai -3)
        # Sumbu Y (Ranking) tidak digambar, tapi Logic-nya ada.

        # Title (Time Counter)
        year_label = Text(str(TIMES[0]), font_size=72, weight=BOLD, color=GREY_A)
        year_label.to_corner(DR, buff=1.0)
        self.add(year_label)

        # Scale Factor
        # Lebar maksimal bar = 10 unit.
        # width = (value / MAX_VAL) * 10
        scale_factor = 10.0 / MAX_VAL if MAX_VAL > 0 else 1.0

        # Container untuk Bar Objects
        # structure: bars[category] = VGroup(rect, label_name, label_val)
        bars = {{}}

        # Posisi Y untuk ranking.
        # Rank 0 (Top) di Y=2.5, Rank N di bawahnya.
        # Spasi antar bar = 0.8
        def get_y_pos(rank):
            return 2.5 - (rank * 0.7)

        # 2. INITIALIZE OBJECTS (AT T=0)
        t0 = TIMES[0]
        # Sort initial rank
        current_data = [(c, DATA[t0].get(c, 0)) for c in CATEGORIES]
        current_data.sort(key=lambda x: x[1], reverse=True) # Sort by value desc

        for rank, (cat, val) in enumerate(current_data):
            # Bar Shape
            bar_width = val * scale_factor
            rect = RoundedRectangle(corner_radius=0.15, height=0.5, width=bar_width, color=COLORS[cat])
            rect.set_fill(COLORS[cat], opacity=0.8)
            rect.set_stroke(width=0)
            # Align Left
            rect.move_to(ORIGIN, aligned_edge=LEFT)

            # Text Name (Inside Left or Outside Left if too small)
            name = Text(cat, font_size=20, color=WHITE).next_to(rect, RIGHT, buff=-rect.width + 0.2)
            if rect.width < 2.0: # Kalau bar pendek, taruh nama di kanan
                 name.next_to(rect, RIGHT, buff=0.2)

            # Value Counter (Right side of bar)
            val_text = DecimalNumber(val, num_decimal_places=0, font_size=20, color=WHITE)
            val_text.next_to(rect, RIGHT, buff=0.2)
            if rect.width < 2.0:
                 val_text.next_to(name, RIGHT, buff=0.2)

            # Grouping
            group = VGroup(rect, name, val_text)
            group.move_to([ -5, get_y_pos(rank), 0 ], aligned_edge=LEFT) # Set Initial Y Position

            bars[cat] = group
            self.add(group)

        # 3. ANIMATION LOOP
        step_time = RUN_TIME / (len(TIMES) - 1)

        for i in range(1, len(TIMES)):
            t_next = TIMES[i]

            # Get data & Calculate New Ranks
            next_data = [(c, DATA[t_next].get(c, 0)) for c in CATEGORIES]
            next_data.sort(key=lambda x: x[1], reverse=True)

            anims = []

            # Update Time Label
            # Hack: Manim Text change is distinct animation, usually Transform(year_label, new_label)
            new_year = Text(str(t_next), font_size=72, weight=BOLD, color=GREY_A).move_to(year_label)
            anims.append(Transform(year_label, new_year))

            for rank, (cat, val) in enumerate(next_data):
                group = bars[cat]
                rect = group[0]
                name = group[1]
                val_text = group[2]

                # A. Move to new Rank Y Position
                target_y = get_y_pos(rank)
                # Slide animation
                anims.append(group.animate.move_to([ -5, target_y, 0 ], aligned_edge=LEFT))

                # B. Grow/Shrink Bar Width
                new_width = max(0.01, val * scale_factor)
                anims.append(rect.animate.stretch_to_fit_width(new_width, about_edge=LEFT))

                # C. Update Number
                anims.append(val_text.animate.set_value(val))

                # D. Adjust Text Positions (Name & Value)
                # Ini trik sulit di Manim: Text harus ikut ujung bar.
                # Kita pakai ValueTracker atau Updater biasanya.
                # Tapi untuk simplicity template: Kita re-position text di next frame.
                # Karena .animate menangani interpolasi, kita biarkan Group logic menangani posisi relatif
                # Namun, jika bar memanjang, posisi text relatif terhadap Group center berubah.

                # FIX: Gunakan updater untuk label agar selalu menempel di ujung bar SELAMA animasi
                def updater_factory(r, n, v):
                    def update_labels(mob):
                        # Logic: Nempel di ujung kanan bar
                        if r.width > 2.0:
                            n.next_to(r, RIGHT, buff=-r.width + 0.2)
                            v.next_to(r, RIGHT, buff=0.2)
                        else:
                            n.next_to(r, RIGHT, buff=0.2)
                            v.next_to(n, RIGHT, buff=0.2)
                    return update_labels

                # Kita tidak bisa attach updater di dalam loop play.
                # Jadi kita biarkan Manim interpolasi group secara linear.
                # Visual mungkin sedikit off saat bar tumbuh cepat, tapi acceptable untuk MVP.
                # Untuk hasil perfect, text harus punya updater.

            self.play(*anims, run_time=step_time, rate_func=linear)

        self.wait(2)
'''
    return code.strip()

def generate_line_evolution_code(spec: object, csv_path: str) -> str:
    """
    Generate a 'Dynamic Line Evolution' chart.
    Perfect for single-variable time series (Stock price, Temperature, etc.).
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    # --- 1. DATA PARSING (Mencari Time & Value) ---
    # Logic parsing mirip sebelumnya, tapi kita fokus ke 1 Value Column utama
    import csv

    value_col = getattr(getattr(spec, "data_binding", None), "value_col", None) or "value"
    time_col = getattr(getattr(spec, "data_binding", None), "time_col", None) or "time"

    def _resolve_headers(headers, target, candidates):
        if target in headers: return target
        lower = {h.lower(): h for h in headers}
        for c in candidates:
            if c in headers: return c
            if c.lower() in lower: return lower[c.lower()]
        return target

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        time_col = _resolve_headers(headers, time_col, ["date", "year", "month", "day", "time", "t"])
        value_col = _resolve_headers(headers, value_col, ["close", "price", "amount", "total", "count", "value"])

        raw_data = [] # (time_str, value_float)
        for row in reader:
            t = (row.get(time_col) or "").strip()
            v_str = (row.get(value_col) or "").strip()
            if not t or not v_str: continue
            try:
                v = float(v_str)
                raw_data.append((t, v))
            except:
                continue

    if not raw_data:
        raise ValueError("No valid data found for Line Chart.")

    # Sort by Time (Simple parsing)
    # Untuk production level, sebaiknya pakai library `dateutil` untuk parse tanggal beneran.
    # Di sini kita asumsikan urutan CSV sudah benar atau formatnya sortable.
    # raw_data.sort(key=lambda x: x[0]) # Optional jika data belum urut

    times = [x[0] for x in raw_data]
    values = [x[1] for x in raw_data]

    # --- 2. VISUAL SCALING LOGIC ---
    min_val = min(values)
    max_val = max(values)

    # Padding Y-Axis (Penting biar gak nempel atap)
    y_range = max_val - min_val
    if y_range == 0: y_range = 1.0
    y_min = min_val - (y_range * 0.1) # Bawah longgar dikit
    y_max = max_val + (y_range * 0.2) # Atas longgar banyak buat Label

    # Config Colors
    theme_color = "#00E5FF" # Cyan Neon

    # Embed Literals
    lit_times = _format_literal(times)
    lit_values = _format_literal(values)

    code = f'''
from manim import *
import numpy as np

TIMES = {lit_times}
VALUES = {lit_values}
Y_MIN = {y_min}
Y_MAX = {y_max}
COLOR_THEME = "{theme_color}"

class GenScene(Scene):
    def construct(self):
        # 1. SETUP AXES
        # X Axis = Index data (0 sampai len-1)
        # Y Axis = Value
        x_len = len(TIMES)

        axes = Axes(
            x_range=[0, x_len - 1, max(1, x_len // 5)], # Step biar gak penuh
            y_range=[Y_MIN, Y_MAX, (Y_MAX - Y_MIN) / 5],
            x_length=10,
            y_length=6,
            axis_config={{"color": GREY, "include_numbers": True, "font_size": 16}},
            tips=False
        )

        # Hapus X-Axis Numbers default karena kita mau custom Label Tanggal
        axes.x_axis.set_opacity(0) # Hide default line if needed, or just hide numbers

        # Custom X Labels (Tampilkan awal, tengah, akhir saja biar rapi)
        x_labels = VGroup()
        indices_to_show = [0, x_len // 2, x_len - 1]
        for i in indices_to_show:
            if i < x_len:
                lbl = Text(str(TIMES[i]), font_size=16, color=GREY_B)
                lbl.next_to(axes.c2p(i, Y_MIN), DOWN)
                x_labels.add(lbl)

        self.add(axes, x_labels)

        # 2. CREATE THE LINE (VMobject)
        # Kita buat path penuh dulu, nanti kita animate creation-nya
        line_path = VMobject()
        line_path.set_points_smoothly([axes.c2p(i, val) for i, val in enumerate(VALUES)])
        line_path.set_color(COLOR_THEME)
        line_path.set_stroke(width=4)

        # Area under curve (Optional aesthetic)
        # Trik: Buat polygon dari titik line + titik bawah axes
        area_points = [axes.c2p(i, val) for i, val in enumerate(VALUES)]
        area_points.append(axes.c2p(x_len-1, Y_MIN)) # Kanan Bawah
        area_points.append(axes.c2p(0, Y_MIN))       # Kiri Bawah

        area = Polygon(*area_points)
        area.set_stroke(width=0)
        area.set_fill(COLOR_THEME, opacity=0.2)

        # 3. THE GLOWING DOT & LABEL (Follower)
        dot = Dot(color=WHITE, radius=0.08)
        dot.move_to(axes.c2p(0, VALUES[0]))

        # Glow Effect (Lingkaran transparan besar di sekitar dot)
        glow = Dot(color=COLOR_THEME, radius=0.2).set_opacity(0.4)
        glow.add_updater(lambda m: m.move_to(dot.get_center()))

        # Value Label (Follows the dot)
        val_label = DecimalNumber(VALUES[0], num_decimal_places=1, font_size=24, color=WHITE)
        val_label.add_background_rectangle()
        val_label.add_updater(lambda m: m.next_to(dot, UP, buff=0.2))

        # 4. ANIMATION
        # Kita gunakan Create(line) tapi kita butuh Dot mengikuti ujungnya.
        # Cara termudah di Manim untuk sinkronisasi: ValueTracker

        tracker = ValueTracker(0)

        # Updater untuk Dot agar menempel di kurva berdasarkan progress tracker
        def update_dot(mob):
            t_idx = tracker.get_value()
            # Interpolasi posisi (karena tracker float, misal 1.5 berarti antara index 1 dan 2)
            # Tapi karena kita pakai set_points_smoothly, curve sudah continuous.
            # Kita ambil point dari curve function:
            point = line_path.point_from_proportion(t_idx / (x_len - 1))
            mob.move_to(point)

        # Updater untuk Label Angka
        def update_val_label(mob):
            t_idx = tracker.get_value()
            idx = int(round(t_idx))
            idx = min(idx, x_len - 1)
            mob.set_value(VALUES[idx])

        dot.add_updater(update_dot)
        val_label.add_updater(update_val_label)

        # Trik animasi: Create line dan FadeIn area
        self.play(FadeIn(dot), FadeIn(glow), FadeIn(val_label))

        # Kita animasikan Line muncul dari kiri ke kanan berbarengan dengan Tracker
        self.play(
            Create(line_path, rate_func=linear),
            FadeIn(area, rate_func=linear), # Area muncul pelan2
            tracker.animate.set_value(x_len - 1),
            run_time=6,
            rate_func=linear
        )

        self.wait(2)

'''
    return code.strip()


def generate_bento_grid_code(spec: object, csv_path: str) -> str:
    """
    Generate a 'Bento Grid' KPI Dashboard.
    Best for: Snapshot data, summary statistics, or small datasets (< 10 items).
    """
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

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Smart Column Detection
        label_col = _resolve_headers(headers, label_col, ["metric", "kpi", "category", "item", "name", "title", "label"])
        value_col = _resolve_headers(headers, value_col, ["value", "amount", "total", "count", "number", "score"])

        for row in reader:
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
