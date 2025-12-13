"""
Visual Elements Module

This module defines the atomic visual elements that can be composed
into data animations. Each element represents a single visual object
with its properties, position, and styling.

Elements are data classes that describe WHAT to render, not HOW.
The actual Manim code generation happens in the codegen module.

Element Types:
- BarElement: Horizontal/vertical bars for bar charts
- BubbleElement: Circles for bubble/scatter charts
- LineElement: Line segments for line charts
- LabelElement: Text labels for data points
- TitleElement: Main title text
- SubtitleElement: Secondary title text
- AnnotationElement: Callout annotations with arrows
- CalloutElement: Highlight callouts without arrows
- TimeDisplayElement: Large time/year display
- LegendElement: Chart legend
- AxisElement: Chart axis with labels
- CardElement: KPI/stat cards for dashboards
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Union
from enum import Enum, auto


# =============================================================================
# ENUMS & TYPES
# =============================================================================

class ElementType(Enum):
    """Types of visual elements"""
    BAR = auto()
    BUBBLE = auto()
    LINE = auto()
    LABEL = auto()
    TITLE = auto()
    SUBTITLE = auto()
    ANNOTATION = auto()
    CALLOUT = auto()
    TIME_DISPLAY = auto()
    LEGEND = auto()
    AXIS = auto()
    CARD = auto()
    GROUP = auto()  # Container for multiple elements


class Anchor(Enum):
    """Anchor points for positioning"""
    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class Direction(Enum):
    """Direction for bars, growth animations, etc."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


# =============================================================================
# POSITION & STYLING
# =============================================================================

@dataclass
class Position:
    """
    Position in the scene coordinate system.

    Manim uses a coordinate system where:
    - X: -7 (left) to 7 (right)
    - Y: -4 (bottom) to 4 (top)
    - Z: depth (usually 0)
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    anchor: Anchor = Anchor.CENTER

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_manim(self) -> str:
        """Generate Manim-compatible position code"""
        return f"[{self.x}, {self.y}, {self.z}]"

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float]) -> "Position":
        return cls(x=t[0], y=t[1], z=t[2] if len(t) > 2 else 0.0)

    def offset(self, dx: float = 0, dy: float = 0, dz: float = 0) -> "Position":
        """Create a new position offset from this one"""
        return Position(
            x=self.x + dx,
            y=self.y + dy,
            z=self.z + dz,
            anchor=self.anchor,
        )


@dataclass
class Style:
    """
    Visual styling for elements.

    Colors should be hex strings (e.g., "#6366F1").
    """
    fill_color: Optional[str] = None
    fill_opacity: float = 1.0
    stroke_color: Optional[str] = None
    stroke_width: float = 0.0
    stroke_opacity: float = 1.0

    # Text-specific
    font_size: Optional[int] = None
    font_weight: Optional[str] = None  # "normal", "bold"
    font_family: Optional[str] = None
    text_color: Optional[str] = None

    # Effects
    shadow: bool = False
    shadow_color: Optional[str] = None
    shadow_offset: Tuple[float, float] = (0.05, -0.05)
    glow: bool = False
    glow_color: Optional[str] = None
    glow_radius: float = 0.2
    corner_radius: float = 0.0

    # Gradient (for advanced styling)
    gradient: bool = False
    gradient_colors: Optional[List[str]] = None
    gradient_direction: Direction = Direction.UP


# =============================================================================
# BASE ELEMENT
# =============================================================================

@dataclass
class Element:
    """
    Base class for all visual elements.

    Every element has:
    - id: Unique identifier for referencing in animations
    - type: What kind of element (bar, bubble, label, etc.)
    - position: Where in the scene
    - style: Visual appearance
    - visible: Whether initially visible
    - data: Associated data values
    - metadata: Extra info for code generation
    """
    id: str
    type: Optional[ElementType] = None  # Set by subclasses in __post_init__
    position: Position = field(default_factory=Position)
    style: Style = field(default_factory=Style)
    visible: bool = True
    layer: int = 0  # Z-ordering (higher = on top)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def clone(self, new_id: Optional[str] = None, **overrides) -> "Element":
        """Create a copy with optional overrides"""
        import copy
        new_elem = copy.deepcopy(self)
        if new_id:
            new_elem.id = new_id
        for key, value in overrides.items():
            if hasattr(new_elem, key):
                setattr(new_elem, key, value)
        return new_elem


# =============================================================================
# CONCRETE ELEMENTS
# =============================================================================

@dataclass
class BarElement(Element):
    """
    A bar for bar charts (horizontal or vertical).

    Attributes:
        width: Bar width
        height: Bar height (represents the data value)
        direction: Which way the bar grows
        value: The numeric value this bar represents
        label: Text label for this bar
        rank: Current ranking position (for bar race)
    """
    width: float = 0.5
    height: float = 1.0
    direction: Direction = Direction.RIGHT
    value: float = 0.0
    label: str = ""
    category: str = ""
    rank: int = 0
    max_width: float = 9.0  # Maximum bar width for scaling

    def __post_init__(self):
        self.type = ElementType.BAR
        if not self.id:
            self.id = f"bar_{self.category}".replace(" ", "_").lower()


@dataclass
class BubbleElement(Element):
    """
    A bubble/circle for bubble charts and scatter plots.

    Attributes:
        radius: Circle radius
        value: Numeric value (often determines radius)
        x_value: X-axis data value
        y_value: Y-axis data value
    """
    radius: float = 0.5
    value: float = 0.0
    x_value: float = 0.0
    y_value: float = 0.0
    entity: str = ""
    group: str = ""

    def __post_init__(self):
        self.type = ElementType.BUBBLE
        if not self.id:
            self.id = f"bubble_{self.entity}".replace(" ", "_").lower()


@dataclass
class LineElement(Element):
    """
    A line segment or path for line charts.

    Attributes:
        points: List of (x, y) coordinates
        smooth: Whether to smooth the line
        area_fill: Whether to fill area under the line
    """
    points: List[Tuple[float, float]] = field(default_factory=list)
    smooth: bool = True
    area_fill: bool = False
    area_opacity: float = 0.2
    line_width: float = 3.0

    def __post_init__(self):
        self.type = ElementType.LINE
        if not self.id:
            self.id = "line_main"


@dataclass
class LabelElement(Element):
    """
    A text label, typically for data values or categories.

    Attributes:
        text: The label text
        format_type: How to format the value (number, currency, percent)
        value: Numeric value (for animated counters)
    """
    text: str = ""
    format_type: str = "text"  # text, number, currency, percent
    value: Optional[float] = None
    prefix: str = ""
    suffix: str = ""
    max_width: Optional[float] = None  # For text truncation

    def __post_init__(self):
        self.type = ElementType.LABEL
        if not self.id:
            self.id = f"label_{self.text[:10]}".replace(" ", "_").lower()


@dataclass
class TitleElement(Element):
    """
    Main title for the animation.
    """
    text: str = ""

    def __post_init__(self):
        self.type = ElementType.TITLE
        self.id = self.id or "title_main"
        # Default title styling
        if self.style.font_size is None:
            self.style.font_size = 48
        if self.style.font_weight is None:
            self.style.font_weight = "bold"


@dataclass
class SubtitleElement(Element):
    """
    Subtitle or description text.
    """
    text: str = ""

    def __post_init__(self):
        self.type = ElementType.SUBTITLE
        self.id = self.id or "subtitle_main"
        # Default subtitle styling
        if self.style.font_size is None:
            self.style.font_size = 24
        if self.style.fill_opacity == 1.0:
            self.style.fill_opacity = 0.7


@dataclass
class AnnotationElement(Element):
    """
    An annotation with optional arrow pointing to something.

    Used for highlighting insights, e.g., "China overtakes Japan!"
    """
    text: str = ""
    target_position: Optional[Position] = None  # Where the arrow points
    arrow: bool = True
    arrow_color: Optional[str] = None
    bubble_style: bool = False  # Speech bubble vs plain text

    def __post_init__(self):
        self.type = ElementType.ANNOTATION
        if not self.id:
            self.id = f"annotation_{id(self)}"


@dataclass
class CalloutElement(Element):
    """
    A highlight callout without arrow (e.g., floating stat).
    """
    text: str = ""
    value: Optional[float] = None
    icon: Optional[str] = None  # Icon name for future use
    background: bool = True

    def __post_init__(self):
        self.type = ElementType.CALLOUT
        if not self.id:
            self.id = f"callout_{id(self)}"


@dataclass
class TimeDisplayElement(Element):
    """
    Large time/year display, typically in corner of animation.
    """
    time: str = ""
    format_pattern: str = "{time}"  # For custom formatting

    def __post_init__(self):
        self.type = ElementType.TIME_DISPLAY
        self.id = self.id or "time_display"
        # Default time display styling
        if self.style.font_size is None:
            self.style.font_size = 72
        if self.style.font_weight is None:
            self.style.font_weight = "bold"
        if self.style.fill_opacity == 1.0:
            self.style.fill_opacity = 0.8


@dataclass
class LegendElement(Element):
    """
    Chart legend showing category colors.
    """
    items: List[Tuple[str, str]] = field(default_factory=list)  # [(label, color), ...]
    orientation: str = "vertical"  # vertical, horizontal

    def __post_init__(self):
        self.type = ElementType.LEGEND
        self.id = self.id or "legend_main"


@dataclass
class AxisElement(Element):
    """
    A chart axis with labels and optional grid.
    """
    axis_type: str = "x"  # x, y
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 10.0
    label: str = ""
    show_grid: bool = False
    show_numbers: bool = True
    custom_labels: Optional[List[str]] = None  # For categorical axes

    def __post_init__(self):
        self.type = ElementType.AXIS
        if not self.id:
            self.id = f"axis_{self.axis_type}"


@dataclass
class CardElement(Element):
    """
    A KPI/stat card for dashboard-style animations.
    """
    title: str = ""
    value: float = 0.0
    change: Optional[float] = None  # Percentage change
    prefix: str = ""
    suffix: str = ""
    icon: Optional[str] = None

    # Card dimensions
    width: float = 2.5
    height: float = 1.8

    def __post_init__(self):
        self.type = ElementType.CARD
        if not self.id:
            self.id = f"card_{self.title}".replace(" ", "_").lower()


@dataclass
class ElementGroup(Element):
    """
    A container for grouping multiple elements.
    Useful for moving/animating multiple elements together.
    """
    children: List[Element] = field(default_factory=list)

    def __post_init__(self):
        self.type = ElementType.GROUP
        if not self.id:
            self.id = f"group_{id(self)}"

    def add(self, element: Element) -> "ElementGroup":
        self.children.append(element)
        return self

    def get_by_id(self, element_id: str) -> Optional[Element]:
        for child in self.children:
            if child.id == element_id:
                return child
            if isinstance(child, ElementGroup):
                found = child.get_by_id(element_id)
                if found:
                    return found
        return None


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_element(
    element_type: Union[ElementType, str],
    id: str,
    **kwargs
) -> Element:
    """
    Factory function to create elements by type.

    Args:
        element_type: Type of element to create
        id: Unique identifier
        **kwargs: Element-specific attributes

    Returns:
        Appropriate Element subclass instance
    """
    if isinstance(element_type, str):
        element_type = ElementType[element_type.upper()]

    type_map = {
        ElementType.BAR: BarElement,
        ElementType.BUBBLE: BubbleElement,
        ElementType.LINE: LineElement,
        ElementType.LABEL: LabelElement,
        ElementType.TITLE: TitleElement,
        ElementType.SUBTITLE: SubtitleElement,
        ElementType.ANNOTATION: AnnotationElement,
        ElementType.CALLOUT: CalloutElement,
        ElementType.TIME_DISPLAY: TimeDisplayElement,
        ElementType.LEGEND: LegendElement,
        ElementType.AXIS: AxisElement,
        ElementType.CARD: CardElement,
        ElementType.GROUP: ElementGroup,
    }

    element_class = type_map.get(element_type, Element)
    return element_class(id=id, **kwargs)


def create_bar(
    id: str,
    category: str,
    value: float,
    color: str,
    position: Optional[Position] = None,
    **kwargs
) -> BarElement:
    """Convenience function to create a bar element"""
    style = Style(fill_color=color, fill_opacity=0.9, corner_radius=0.12)
    return BarElement(
        id=id,
        category=category,
        value=value,
        label=category,
        position=position or Position(),
        style=style,
        **kwargs
    )


def create_title(
    text: str,
    color: str = "#FFFFFF",
    position: Optional[Position] = None,
    **kwargs
) -> TitleElement:
    """Convenience function to create a title element"""
    if position is None:
        position = Position(x=0, y=3.5, anchor=Anchor.CENTER)
    style = Style(text_color=color, font_size=48, font_weight="bold")
    return TitleElement(
        id="title_main",
        text=text,
        position=position,
        style=style,
        **kwargs
    )


def create_annotation(
    text: str,
    position: Position,
    target: Optional[Position] = None,
    color: str = "#22D3EE",
    **kwargs
) -> AnnotationElement:
    """Convenience function to create an annotation"""
    style = Style(text_color=color, font_size=20)
    return AnnotationElement(
        id=f"annotation_{id(text)}",
        text=text,
        position=position,
        target_position=target,
        style=style,
        **kwargs
    )
