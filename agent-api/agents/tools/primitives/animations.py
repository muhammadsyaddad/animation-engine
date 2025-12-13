"""
Animation Types Module

This module defines reusable animation primitives that can be applied
to any visual element. Animations describe HOW elements appear, move,
transform, and disappear.

Animation Categories:
- Entrance: FadeIn, GrowFrom, SlideIn, PopIn, TypeWriter
- Exit: FadeOut, ShrinkTo, SlideOut, PopOut
- Emphasis: Pulse, Shake, Bounce, Glow, Wiggle
- Transform: Morph, CountUp, ColorShift, Scale
- Motion: MoveTo, Follow, Orbit
- Compound: Stagger, Sequence, Parallel

Each animation can be customized with:
- Duration
- Easing function
- Delay
- Custom parameters
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Union, Callable
from enum import Enum, auto


# =============================================================================
# ENUMS
# =============================================================================

class AnimationType(Enum):
    """All available animation types"""
    # Entrance animations
    FADE_IN = auto()
    GROW_FROM_CENTER = auto()
    GROW_FROM_EDGE = auto()
    SLIDE_IN = auto()
    POP_IN = auto()
    TYPE_WRITER = auto()
    DRAW = auto()  # For lines/paths
    COUNT_IN = auto()  # For numbers counting from 0

    # Exit animations
    FADE_OUT = auto()
    SHRINK_TO_CENTER = auto()
    SHRINK_TO_EDGE = auto()
    SLIDE_OUT = auto()
    POP_OUT = auto()

    # Emphasis animations
    PULSE = auto()
    SHAKE = auto()
    BOUNCE = auto()
    GLOW = auto()
    WIGGLE = auto()
    FLASH = auto()
    INDICATE = auto()

    # Transform animations
    MORPH = auto()
    COUNT_UP = auto()  # Animate number value change
    COUNT_DOWN = auto()
    COLOR_SHIFT = auto()
    SCALE = auto()
    ROTATE = auto()

    # Motion animations
    MOVE_TO = auto()
    MOVE_BY = auto()
    FOLLOW_PATH = auto()
    ORBIT = auto()

    # Compound animations
    STAGGER = auto()  # Apply same animation with delay
    SEQUENCE = auto()  # Play animations one after another
    PARALLEL = auto()  # Play animations simultaneously

    # Special
    WAIT = auto()
    CUSTOM = auto()


class EasingType(Enum):
    """Easing functions for smooth animations"""
    LINEAR = "linear"
    SMOOTH = "smooth"  # Manim's default smooth
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"

    # Cubic
    EASE_IN_CUBIC = "ease_in_cubic"
    EASE_OUT_CUBIC = "ease_out_cubic"
    EASE_IN_OUT_CUBIC = "ease_in_out_cubic"

    # Bounce
    EASE_OUT_BOUNCE = "ease_out_bounce"
    EASE_IN_BOUNCE = "ease_in_bounce"

    # Elastic
    EASE_OUT_ELASTIC = "ease_out_elastic"
    EASE_IN_ELASTIC = "ease_in_elastic"

    # Back (overshoot)
    EASE_OUT_BACK = "ease_out_back"
    EASE_IN_BACK = "ease_in_back"

    # Special
    THERE_AND_BACK = "there_and_back"
    RUSH_INTO = "rush_into"
    RUSH_FROM = "rush_from"
    DOUBLE_SMOOTH = "double_smooth"


class Direction(Enum):
    """Direction for directional animations"""
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    IN = "IN"  # Towards center
    OUT = "OUT"  # Away from center


# =============================================================================
# ANIMATION CONFIG
# =============================================================================

@dataclass
class AnimationConfig:
    """
    Configuration for a single animation.

    This is the core building block - every animation applied to an element
    uses this configuration.
    """
    type: AnimationType
    duration: float = 1.0
    delay: float = 0.0
    easing: EasingType = EasingType.SMOOTH

    # Target element (by ID)
    target_id: Optional[str] = None

    # Direction for directional animations
    direction: Direction = Direction.UP

    # Transform target (for MORPH, MOVE_TO, etc.)
    to_value: Any = None
    from_value: Any = None

    # Scale factors
    scale_factor: float = 1.0

    # Color for color-related animations
    color: Optional[str] = None
    to_color: Optional[str] = None

    # Emphasis parameters
    intensity: float = 1.0  # How strong the effect is
    repeat: int = 1  # Number of times to repeat

    # Stagger parameters
    stagger_delay: float = 0.1  # Delay between each element

    # Custom parameters for extensibility
    params: Dict[str, Any] = field(default_factory=dict)

    def with_delay(self, delay: float) -> "AnimationConfig":
        """Create a copy with modified delay"""
        import copy
        new_config = copy.deepcopy(self)
        new_config.delay = delay
        return new_config

    def with_duration(self, duration: float) -> "AnimationConfig":
        """Create a copy with modified duration"""
        import copy
        new_config = copy.deepcopy(self)
        new_config.duration = duration
        return new_config

    @property
    def total_time(self) -> float:
        """Total time including delay"""
        return self.delay + self.duration


@dataclass
class AnimationSequence:
    """
    A sequence of animations to be played together or in order.

    Modes:
    - PARALLEL: All animations play at the same time
    - SEQUENCE: Animations play one after another
    - STAGGER: Same animation applied to multiple elements with delay
    """
    animations: List[AnimationConfig] = field(default_factory=list)
    mode: str = "parallel"  # parallel, sequence, stagger
    name: Optional[str] = None

    def add(self, animation: AnimationConfig) -> "AnimationSequence":
        """Add an animation to the sequence"""
        self.animations.append(animation)
        return self

    @property
    def total_duration(self) -> float:
        """Calculate total duration of the sequence"""
        if not self.animations:
            return 0.0

        if self.mode == "parallel":
            return max(a.total_time for a in self.animations)
        elif self.mode == "sequence":
            return sum(a.total_time for a in self.animations)
        else:  # stagger
            if len(self.animations) == 1:
                return self.animations[0].total_time
            stagger = self.animations[0].stagger_delay if self.animations else 0.1
            base_duration = self.animations[0].duration if self.animations else 1.0
            return base_duration + (len(self.animations) - 1) * stagger

    def as_parallel(self) -> "AnimationSequence":
        """Convert to parallel mode"""
        self.mode = "parallel"
        return self

    def as_sequence(self) -> "AnimationSequence":
        """Convert to sequential mode"""
        self.mode = "sequence"
        return self


# =============================================================================
# ANIMATION PRESETS
# =============================================================================

# Pre-configured animations for common use cases
ANIMATION_PRESETS: Dict[str, AnimationConfig] = {
    # Entrance
    "fade_in": AnimationConfig(
        type=AnimationType.FADE_IN,
        duration=0.5,
        easing=EasingType.SMOOTH,
    ),
    "fade_in_slow": AnimationConfig(
        type=AnimationType.FADE_IN,
        duration=1.0,
        easing=EasingType.EASE_IN_OUT,
    ),
    "grow_in": AnimationConfig(
        type=AnimationType.GROW_FROM_CENTER,
        duration=0.5,
        easing=EasingType.EASE_OUT_BACK,
    ),
    "grow_from_bottom": AnimationConfig(
        type=AnimationType.GROW_FROM_EDGE,
        duration=0.6,
        direction=Direction.UP,
        easing=EasingType.EASE_OUT_CUBIC,
    ),
    "grow_from_left": AnimationConfig(
        type=AnimationType.GROW_FROM_EDGE,
        duration=0.6,
        direction=Direction.RIGHT,
        easing=EasingType.EASE_OUT_CUBIC,
    ),
    "slide_in_left": AnimationConfig(
        type=AnimationType.SLIDE_IN,
        duration=0.5,
        direction=Direction.RIGHT,
        easing=EasingType.EASE_OUT_CUBIC,
    ),
    "slide_in_bottom": AnimationConfig(
        type=AnimationType.SLIDE_IN,
        duration=0.5,
        direction=Direction.UP,
        easing=EasingType.EASE_OUT_CUBIC,
    ),
    "pop_in": AnimationConfig(
        type=AnimationType.POP_IN,
        duration=0.4,
        easing=EasingType.EASE_OUT_BACK,
        scale_factor=1.2,
    ),
    "typewriter": AnimationConfig(
        type=AnimationType.TYPE_WRITER,
        duration=1.0,
        easing=EasingType.LINEAR,
    ),
    "draw_line": AnimationConfig(
        type=AnimationType.DRAW,
        duration=2.0,
        easing=EasingType.LINEAR,
    ),
    "count_in": AnimationConfig(
        type=AnimationType.COUNT_IN,
        duration=1.5,
        easing=EasingType.EASE_OUT_CUBIC,
    ),

    # Exit
    "fade_out": AnimationConfig(
        type=AnimationType.FADE_OUT,
        duration=0.5,
        easing=EasingType.SMOOTH,
    ),
    "shrink_out": AnimationConfig(
        type=AnimationType.SHRINK_TO_CENTER,
        duration=0.4,
        easing=EasingType.EASE_IN_BACK,
    ),
    "slide_out_right": AnimationConfig(
        type=AnimationType.SLIDE_OUT,
        duration=0.5,
        direction=Direction.RIGHT,
        easing=EasingType.EASE_IN_CUBIC,
    ),

    # Emphasis
    "pulse": AnimationConfig(
        type=AnimationType.PULSE,
        duration=0.6,
        easing=EasingType.SMOOTH,
        scale_factor=1.15,
        repeat=1,
    ),
    "pulse_strong": AnimationConfig(
        type=AnimationType.PULSE,
        duration=0.8,
        easing=EasingType.SMOOTH,
        scale_factor=1.3,
        repeat=2,
    ),
    "shake": AnimationConfig(
        type=AnimationType.SHAKE,
        duration=0.5,
        intensity=0.1,
        repeat=3,
    ),
    "bounce": AnimationConfig(
        type=AnimationType.BOUNCE,
        duration=0.6,
        easing=EasingType.EASE_OUT_BOUNCE,
    ),
    "glow": AnimationConfig(
        type=AnimationType.GLOW,
        duration=0.8,
        intensity=1.5,
        easing=EasingType.THERE_AND_BACK,
    ),
    "wiggle": AnimationConfig(
        type=AnimationType.WIGGLE,
        duration=0.5,
        intensity=0.15,
        repeat=3,
    ),
    "flash": AnimationConfig(
        type=AnimationType.FLASH,
        duration=0.3,
        repeat=2,
    ),
    "indicate": AnimationConfig(
        type=AnimationType.INDICATE,
        duration=0.8,
        easing=EasingType.THERE_AND_BACK,
        scale_factor=1.2,
    ),

    # Transform
    "morph": AnimationConfig(
        type=AnimationType.MORPH,
        duration=0.8,
        easing=EasingType.SMOOTH,
    ),
    "morph_fast": AnimationConfig(
        type=AnimationType.MORPH,
        duration=0.4,
        easing=EasingType.EASE_OUT_CUBIC,
    ),
    "count_up": AnimationConfig(
        type=AnimationType.COUNT_UP,
        duration=1.5,
        easing=EasingType.EASE_OUT_CUBIC,
    ),
    "color_shift": AnimationConfig(
        type=AnimationType.COLOR_SHIFT,
        duration=0.5,
        easing=EasingType.SMOOTH,
    ),

    # Motion
    "move_to": AnimationConfig(
        type=AnimationType.MOVE_TO,
        duration=0.8,
        easing=EasingType.SMOOTH,
    ),
    "move_smooth": AnimationConfig(
        type=AnimationType.MOVE_TO,
        duration=1.0,
        easing=EasingType.EASE_IN_OUT_CUBIC,
    ),

    # Utility
    "wait_short": AnimationConfig(
        type=AnimationType.WAIT,
        duration=0.5,
    ),
    "wait_medium": AnimationConfig(
        type=AnimationType.WAIT,
        duration=1.0,
    ),
    "wait_long": AnimationConfig(
        type=AnimationType.WAIT,
        duration=2.0,
    ),
}


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_animation(
    animation_type: Union[AnimationType, str],
    duration: float = 1.0,
    **kwargs
) -> AnimationConfig:
    """
    Create an animation configuration.

    Args:
        animation_type: Type of animation
        duration: Animation duration in seconds
        **kwargs: Additional animation parameters

    Returns:
        AnimationConfig instance
    """
    if isinstance(animation_type, str):
        # Check if it's a preset name
        if animation_type in ANIMATION_PRESETS:
            preset = ANIMATION_PRESETS[animation_type]
            import copy
            config = copy.deepcopy(preset)
            config.duration = duration
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            return config
        # Otherwise try to parse as enum
        animation_type = AnimationType[animation_type.upper()]

    return AnimationConfig(
        type=animation_type,
        duration=duration,
        **kwargs
    )


def create_staggered_animation(
    animation_type: Union[AnimationType, str],
    target_ids: List[str],
    stagger_delay: float = 0.1,
    duration: float = 0.5,
    **kwargs
) -> AnimationSequence:
    """
    Create a staggered animation that applies to multiple elements.

    Args:
        animation_type: Type of animation to apply
        target_ids: List of element IDs to animate
        stagger_delay: Delay between each element's animation
        duration: Duration of each individual animation
        **kwargs: Additional animation parameters

    Returns:
        AnimationSequence with staggered animations
    """
    animations = []
    for i, target_id in enumerate(target_ids):
        anim = create_animation(
            animation_type,
            duration=duration,
            delay=i * stagger_delay,
            target_id=target_id,
            **kwargs
        )
        animations.append(anim)

    return AnimationSequence(
        animations=animations,
        mode="stagger",
        name=f"stagger_{animation_type}",
    )


def create_emphasis_animation(
    target_id: str,
    emphasis_type: str = "pulse",
    duration: float = 0.6,
    intensity: float = 1.0,
) -> AnimationConfig:
    """
    Create an emphasis animation for highlighting elements.

    Args:
        target_id: Element to emphasize
        emphasis_type: Type of emphasis (pulse, shake, bounce, glow, wiggle)
        duration: Animation duration
        intensity: How strong the effect is

    Returns:
        AnimationConfig for emphasis
    """
    type_map = {
        "pulse": AnimationType.PULSE,
        "shake": AnimationType.SHAKE,
        "bounce": AnimationType.BOUNCE,
        "glow": AnimationType.GLOW,
        "wiggle": AnimationType.WIGGLE,
        "flash": AnimationType.FLASH,
        "indicate": AnimationType.INDICATE,
    }

    anim_type = type_map.get(emphasis_type, AnimationType.PULSE)

    return AnimationConfig(
        type=anim_type,
        target_id=target_id,
        duration=duration,
        intensity=intensity,
        easing=EasingType.THERE_AND_BACK if emphasis_type in ["pulse", "glow"] else EasingType.SMOOTH,
    )


def create_entrance_sequence(
    target_ids: List[str],
    style: str = "fade_stagger",
    total_duration: float = 1.5,
) -> AnimationSequence:
    """
    Create an entrance animation sequence for multiple elements.

    Styles:
    - fade_stagger: Fade in with stagger
    - grow_stagger: Grow from bottom with stagger
    - slide_stagger: Slide in with stagger
    - pop_stagger: Pop in with stagger
    - cascade: Cascade from top to bottom
    - explode: All pop in from center

    Args:
        target_ids: Elements to animate
        style: Animation style
        total_duration: Total time for all elements to appear

    Returns:
        AnimationSequence
    """
    n = len(target_ids)
    if n == 0:
        return AnimationSequence(animations=[], mode="parallel")

    # Calculate per-element timing
    overlap = 0.7  # 70% overlap between animations
    single_duration = total_duration / (1 + (n - 1) * (1 - overlap)) if n > 1 else total_duration
    stagger = single_duration * (1 - overlap)

    style_map = {
        "fade_stagger": (AnimationType.FADE_IN, Direction.UP),
        "grow_stagger": (AnimationType.GROW_FROM_EDGE, Direction.UP),
        "slide_stagger": (AnimationType.SLIDE_IN, Direction.LEFT),
        "pop_stagger": (AnimationType.POP_IN, Direction.UP),
        "cascade": (AnimationType.FADE_IN, Direction.DOWN),
        "explode": (AnimationType.GROW_FROM_CENTER, Direction.OUT),
    }

    anim_type, direction = style_map.get(style, (AnimationType.FADE_IN, Direction.UP))

    animations = []
    for i, target_id in enumerate(target_ids):
        animations.append(AnimationConfig(
            type=anim_type,
            target_id=target_id,
            duration=single_duration,
            delay=i * stagger,
            direction=direction,
            easing=EasingType.EASE_OUT_CUBIC,
        ))

    return AnimationSequence(
        animations=animations,
        mode="stagger",
        name=f"entrance_{style}",
    )


def create_exit_sequence(
    target_ids: List[str],
    style: str = "fade_stagger",
    total_duration: float = 1.0,
) -> AnimationSequence:
    """
    Create an exit animation sequence for multiple elements.

    Args:
        target_ids: Elements to animate
        style: Animation style (fade_stagger, shrink_stagger, slide_stagger)
        total_duration: Total time for all elements to disappear

    Returns:
        AnimationSequence
    """
    n = len(target_ids)
    if n == 0:
        return AnimationSequence(animations=[], mode="parallel")

    single_duration = total_duration / n if n > 1 else total_duration
    stagger = single_duration * 0.5

    style_map = {
        "fade_stagger": AnimationType.FADE_OUT,
        "shrink_stagger": AnimationType.SHRINK_TO_CENTER,
        "slide_stagger": AnimationType.SLIDE_OUT,
    }

    anim_type = style_map.get(style, AnimationType.FADE_OUT)

    animations = []
    for i, target_id in enumerate(target_ids):
        animations.append(AnimationConfig(
            type=anim_type,
            target_id=target_id,
            duration=single_duration,
            delay=i * stagger,
            easing=EasingType.EASE_IN_CUBIC,
        ))

    return AnimationSequence(
        animations=animations,
        mode="stagger",
        name=f"exit_{style}",
    )


def create_morph_animation(
    target_id: str,
    duration: float = 0.8,
    easing: EasingType = EasingType.SMOOTH,
) -> AnimationConfig:
    """
    Create a morph/transform animation.

    Used when an element changes shape, size, or position smoothly.

    Args:
        target_id: Element to morph
        duration: Animation duration
        easing: Easing function

    Returns:
        AnimationConfig for morphing
    """
    return AnimationConfig(
        type=AnimationType.MORPH,
        target_id=target_id,
        duration=duration,
        easing=easing,
    )


def create_count_animation(
    target_id: str,
    from_value: float,
    to_value: float,
    duration: float = 1.5,
) -> AnimationConfig:
    """
    Create a counting animation for numeric values.

    Args:
        target_id: Element containing the number
        from_value: Starting value
        to_value: Ending value
        duration: Animation duration

    Returns:
        AnimationConfig for counting
    """
    return AnimationConfig(
        type=AnimationType.COUNT_UP if to_value > from_value else AnimationType.COUNT_DOWN,
        target_id=target_id,
        from_value=from_value,
        to_value=to_value,
        duration=duration,
        easing=EasingType.EASE_OUT_CUBIC,
    )


# =============================================================================
# EASING FUNCTION CODE GENERATION
# =============================================================================

def get_easing_code(easing: EasingType) -> str:
    """
    Get the Manim rate_func code for an easing type.

    Args:
        easing: Easing type

    Returns:
        String of Manim rate_func
    """
    easing_map = {
        EasingType.LINEAR: "linear",
        EasingType.SMOOTH: "smooth",
        EasingType.EASE_IN: "ease_in_sine",
        EasingType.EASE_OUT: "ease_out_sine",
        EasingType.EASE_IN_OUT: "ease_in_out_sine",
        EasingType.EASE_IN_CUBIC: "ease_in_cubic",
        EasingType.EASE_OUT_CUBIC: "ease_out_cubic",
        EasingType.EASE_IN_OUT_CUBIC: "ease_in_out_cubic",
        EasingType.EASE_OUT_BOUNCE: "ease_out_bounce",
        EasingType.EASE_IN_BOUNCE: "ease_in_bounce",
        EasingType.EASE_OUT_ELASTIC: "ease_out_elastic",
        EasingType.EASE_IN_ELASTIC: "ease_in_elastic",
        EasingType.EASE_OUT_BACK: "ease_out_back",
        EasingType.EASE_IN_BACK: "ease_in_back",
        EasingType.THERE_AND_BACK: "there_and_back",
        EasingType.RUSH_INTO: "rush_into",
        EasingType.RUSH_FROM: "rush_from",
        EasingType.DOUBLE_SMOOTH: "double_smooth",
    }
    return easing_map.get(easing, "smooth")


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Animation Primitives Module Loaded Successfully")
    print(f"Available animation types: {len(AnimationType)}")
    print(f"Available presets: {len(ANIMATION_PRESETS)}")

    # Test creating animations
    fade = create_animation("fade_in", duration=0.5)
    print(f"\nFade in: {fade}")

    stagger = create_staggered_animation(
        "grow_from_bottom",
        target_ids=["bar_1", "bar_2", "bar_3"],
        stagger_delay=0.1,
    )
    print(f"\nStagger sequence: {stagger.total_duration}s total")

    entrance = create_entrance_sequence(
        ["elem_1", "elem_2", "elem_3", "elem_4"],
        style="pop_stagger",
        total_duration=2.0,
    )
    print(f"\nEntrance sequence: {entrance.total_duration}s total")
