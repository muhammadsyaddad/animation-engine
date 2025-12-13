"""
Scenes Module

This module defines story beats - the building blocks of narrative-driven
data animations. Scenes compose elements and animations into meaningful
story segments.

Scene Types:
- INTRO: Title, subtitle, set the stage
- REVEAL: Data appears for the first time
- DATA: Main data visualization (the "race", "evolution", etc.)
- HIGHLIGHT: Call attention to specific insights
- TRANSITION: Move between different views or time periods
- COMPARISON: Side-by-side or before/after comparisons
- CONCLUSION: Summary, final stats, call to action

Each scene defines:
- What elements appear
- What animations play
- How long it lasts
- Any narrative text or annotations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Union, Callable
from enum import Enum, auto

from agents.tools.primitives.elements import (
    Element,
    ElementType,
    Position,
    Style,
    TitleElement,
    SubtitleElement,
    AnnotationElement,
    TimeDisplayElement,
)
from agents.tools.primitives.animations import (
    AnimationType,
    AnimationConfig,
    AnimationSequence,
    EasingType,
    create_animation,
    create_staggered_animation,
    create_entrance_sequence,
    ANIMATION_PRESETS,
)


# =============================================================================
# ENUMS
# =============================================================================

class SceneType(Enum):
    """Types of story scenes"""
    INTRO = auto()          # Opening: title, subtitle, hook
    REVEAL = auto()         # Data first appears
    DATA = auto()           # Main data animation (race, evolution, etc.)
    HIGHLIGHT = auto()      # Call out specific insight
    TRANSITION = auto()     # Move between views/times
    COMPARISON = auto()     # Compare two states
    ANNOTATION = auto()     # Add explanatory text
    PAUSE = auto()          # Dramatic pause
    CONCLUSION = auto()     # Wrap up, summary stats


class TransitionStyle(Enum):
    """How scenes transition to each other"""
    CUT = "cut"             # Instant switch
    FADE = "fade"           # Fade through black
    CROSSFADE = "crossfade" # Elements fade into each other
    WIPE = "wipe"           # Wipe left/right/up/down
    ZOOM = "zoom"           # Zoom in/out
    MORPH = "morph"         # Elements morph into new state


class NarrativeRole(Enum):
    """Role of a scene in the narrative arc"""
    HOOK = "hook"           # Grab attention
    CONTEXT = "context"     # Set up the situation
    RISING = "rising"       # Build tension/interest
    CLIMAX = "climax"       # Peak moment
    FALLING = "falling"     # After the peak
    RESOLUTION = "resolution"  # Wrap up


# =============================================================================
# SCENE ELEMENT
# =============================================================================

@dataclass
class SceneElement:
    """
    An element within a scene with its entrance/exit animations.

    This links an Element to when and how it appears in the scene.
    """
    element: Element
    entrance: Optional[AnimationConfig] = None
    exit: Optional[AnimationConfig] = None

    # Timing relative to scene start
    enter_at: float = 0.0      # When to start entrance (seconds from scene start)
    exit_at: Optional[float] = None  # When to start exit (None = stays until scene end)

    # Whether element persists to next scene
    persist: bool = False

    # Emphasis animation to play during scene
    emphasis: Optional[AnimationConfig] = None
    emphasis_at: Optional[float] = None

    def __post_init__(self):
        # Set default entrance if not specified
        if self.entrance is None:
            self.entrance = AnimationConfig(
                type=AnimationType.FADE_IN,
                duration=0.5,
                target_id=self.element.id,
            )
        else:
            self.entrance.target_id = self.element.id

        if self.exit is not None:
            self.exit.target_id = self.element.id


# =============================================================================
# SCENE CONFIG
# =============================================================================

@dataclass
class SceneConfig:
    """
    Configuration for a single scene in the story.

    A scene is a coherent segment of the animation with:
    - A clear purpose (intro, reveal, highlight, etc.)
    - A set of elements
    - Animations that bring it to life
    - Defined duration and timing
    """
    type: SceneType
    duration: float = 2.0
    name: Optional[str] = None

    # Elements in this scene
    elements: List[SceneElement] = field(default_factory=list)

    # Animations to play (beyond element entrance/exit)
    animations: List[AnimationConfig] = field(default_factory=list)

    # Animation sequences (for complex choreography)
    sequences: List[AnimationSequence] = field(default_factory=list)

    # Narrative role
    narrative_role: NarrativeRole = NarrativeRole.CONTEXT

    # Transition to next scene
    transition_out: TransitionStyle = TransitionStyle.CUT
    transition_duration: float = 0.5

    # Scene-specific content
    title: Optional[str] = None
    subtitle: Optional[str] = None
    annotation: Optional[str] = None

    # For DATA scenes: which time period(s) to show
    time_range: Optional[Tuple[str, str]] = None  # (start_time, end_time)

    # For HIGHLIGHT scenes: what to emphasize
    highlight_elements: List[str] = field(default_factory=list)  # Element IDs
    highlight_text: Optional[str] = None

    # Custom parameters
    params: Dict[str, Any] = field(default_factory=dict)

    def add_element(
        self,
        element: Element,
        entrance: Optional[AnimationConfig] = None,
        enter_at: float = 0.0,
        persist: bool = False,
    ) -> "SceneConfig":
        """Add an element to the scene"""
        self.elements.append(SceneElement(
            element=element,
            entrance=entrance,
            enter_at=enter_at,
            persist=persist,
        ))
        return self

    def add_animation(self, animation: AnimationConfig) -> "SceneConfig":
        """Add an animation to the scene"""
        self.animations.append(animation)
        return self

    def add_sequence(self, sequence: AnimationSequence) -> "SceneConfig":
        """Add an animation sequence to the scene"""
        self.sequences.append(sequence)
        return self

    @property
    def total_duration(self) -> float:
        """Total duration including transition"""
        return self.duration + self.transition_duration

    def get_element_ids(self) -> List[str]:
        """Get all element IDs in this scene"""
        return [se.element.id for se in self.elements]


# =============================================================================
# SCENE PRESETS
# =============================================================================

SCENE_PRESETS: Dict[str, SceneConfig] = {
    # Basic intro with title fade in
    "intro_simple": SceneConfig(
        type=SceneType.INTRO,
        duration=2.5,
        name="Simple Intro",
        narrative_role=NarrativeRole.HOOK,
        transition_out=TransitionStyle.FADE,
        transition_duration=0.5,
    ),

    # Dramatic intro with title + subtitle
    "intro_dramatic": SceneConfig(
        type=SceneType.INTRO,
        duration=4.0,
        name="Dramatic Intro",
        narrative_role=NarrativeRole.HOOK,
        transition_out=TransitionStyle.CROSSFADE,
        transition_duration=0.8,
    ),

    # Data reveal with staggered bars
    "reveal_stagger": SceneConfig(
        type=SceneType.REVEAL,
        duration=2.0,
        name="Staggered Reveal",
        narrative_role=NarrativeRole.CONTEXT,
        transition_out=TransitionStyle.CUT,
    ),

    # Main data race
    "data_race": SceneConfig(
        type=SceneType.DATA,
        duration=15.0,
        name="Data Race",
        narrative_role=NarrativeRole.RISING,
        transition_out=TransitionStyle.CUT,
    ),

    # Highlight a specific insight
    "highlight_insight": SceneConfig(
        type=SceneType.HIGHLIGHT,
        duration=2.0,
        name="Insight Highlight",
        narrative_role=NarrativeRole.CLIMAX,
        transition_out=TransitionStyle.FADE,
        transition_duration=0.3,
    ),

    # Conclusion with summary
    "conclusion_summary": SceneConfig(
        type=SceneType.CONCLUSION,
        duration=3.0,
        name="Summary Conclusion",
        narrative_role=NarrativeRole.RESOLUTION,
        transition_out=TransitionStyle.FADE,
        transition_duration=1.0,
    ),

    # Quick pause for dramatic effect
    "pause_dramatic": SceneConfig(
        type=SceneType.PAUSE,
        duration=1.0,
        name="Dramatic Pause",
        narrative_role=NarrativeRole.CLIMAX,
        transition_out=TransitionStyle.CUT,
    ),
}


# =============================================================================
# SCENE BUILDERS
# =============================================================================

def create_intro_scene(
    title: str,
    subtitle: Optional[str] = None,
    duration: float = 3.0,
    title_color: str = "#FFFFFF",
    subtitle_color: str = "#A1A1AA",
    background_color: Optional[str] = None,
    animation_style: str = "fade",  # fade, typewriter, pop
) -> SceneConfig:
    """
    Create an intro scene with title and optional subtitle.

    Args:
        title: Main title text
        subtitle: Optional subtitle text
        duration: Scene duration in seconds
        title_color: Color for title text
        subtitle_color: Color for subtitle text
        background_color: Optional background color
        animation_style: How text appears (fade, typewriter, pop)

    Returns:
        Configured intro scene
    """
    scene = SceneConfig(
        type=SceneType.INTRO,
        duration=duration,
        name=f"Intro: {title[:20]}...",
        title=title,
        subtitle=subtitle,
        narrative_role=NarrativeRole.HOOK,
        transition_out=TransitionStyle.FADE,
        transition_duration=0.5,
    )

    # Create title element
    title_elem = TitleElement(
        id="intro_title",
        text=title,
        position=Position(x=0, y=0.5 if subtitle else 0),
        style=Style(text_color=title_color, font_size=56, font_weight="bold"),
    )

    # Animation based on style
    if animation_style == "typewriter":
        title_anim = AnimationConfig(
            type=AnimationType.TYPE_WRITER,
            duration=duration * 0.5,
            target_id="intro_title",
        )
    elif animation_style == "pop":
        title_anim = AnimationConfig(
            type=AnimationType.POP_IN,
            duration=0.6,
            target_id="intro_title",
            easing=EasingType.EASE_OUT_BACK,
        )
    else:  # fade
        title_anim = AnimationConfig(
            type=AnimationType.FADE_IN,
            duration=0.8,
            target_id="intro_title",
            easing=EasingType.EASE_OUT_CUBIC,
        )

    scene.add_element(title_elem, entrance=title_anim, enter_at=0.2)

    # Add subtitle if provided
    if subtitle:
        subtitle_elem = SubtitleElement(
            id="intro_subtitle",
            text=subtitle,
            position=Position(x=0, y=-0.5),
            style=Style(text_color=subtitle_color, font_size=28, fill_opacity=0.8),
        )

        subtitle_anim = AnimationConfig(
            type=AnimationType.FADE_IN,
            duration=0.6,
            target_id="intro_subtitle",
            easing=EasingType.EASE_OUT_CUBIC,
        )

        scene.add_element(subtitle_elem, entrance=subtitle_anim, enter_at=0.8)

    if background_color:
        scene.params["background_color"] = background_color

    return scene


def create_reveal_scene(
    element_ids: List[str],
    duration: float = 2.0,
    style: str = "stagger",  # stagger, cascade, explode, simultaneous
    stagger_delay: float = 0.1,
    with_time_display: bool = False,
    time_value: Optional[str] = None,
) -> SceneConfig:
    """
    Create a reveal scene where data elements first appear.

    Args:
        element_ids: IDs of elements to reveal
        duration: Scene duration
        style: Animation style for reveal
        stagger_delay: Delay between elements (for stagger style)
        with_time_display: Whether to show time/year
        time_value: Value for time display

    Returns:
        Configured reveal scene
    """
    scene = SceneConfig(
        type=SceneType.REVEAL,
        duration=duration,
        name="Data Reveal",
        narrative_role=NarrativeRole.CONTEXT,
        transition_out=TransitionStyle.CUT,
    )

    # Create entrance sequence based on style
    if style == "simultaneous":
        # All at once
        for elem_id in element_ids:
            scene.add_animation(AnimationConfig(
                type=AnimationType.GROW_FROM_EDGE,
                target_id=elem_id,
                duration=duration * 0.6,
                easing=EasingType.EASE_OUT_CUBIC,
            ))
    else:
        # Staggered entrance
        entrance_seq = create_entrance_sequence(
            target_ids=element_ids,
            style=f"{style.replace('stagger', 'grow')}_stagger" if 'stagger' in style else style,
            total_duration=duration * 0.8,
        )
        scene.add_sequence(entrance_seq)

    # Add time display if requested
    if with_time_display and time_value:
        scene.params["time_display"] = time_value

    return scene


def create_data_scene(
    duration: float = 15.0,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    step_duration: Optional[float] = None,
    highlight_changes: bool = True,
    show_annotations: bool = True,
) -> SceneConfig:
    """
    Create the main data animation scene (the "race", "evolution", etc.).

    This is typically the longest scene where data transforms over time.

    Args:
        duration: Total duration for the data animation
        time_start: Starting time period
        time_end: Ending time period
        step_duration: Duration for each time step (auto-calculated if None)
        highlight_changes: Whether to emphasize major changes
        show_annotations: Whether to show auto-generated annotations

    Returns:
        Configured data scene
    """
    scene = SceneConfig(
        type=SceneType.DATA,
        duration=duration,
        name="Data Animation",
        narrative_role=NarrativeRole.RISING,
        transition_out=TransitionStyle.CUT,
    )

    if time_start and time_end:
        scene.time_range = (time_start, time_end)

    scene.params["step_duration"] = step_duration
    scene.params["highlight_changes"] = highlight_changes
    scene.params["show_annotations"] = show_annotations

    return scene


def create_highlight_scene(
    element_ids: List[str],
    annotation_text: Optional[str] = None,
    duration: float = 2.0,
    emphasis_type: str = "pulse",  # pulse, glow, shake, indicate
    dim_others: bool = True,
) -> SceneConfig:
    """
    Create a highlight scene to call attention to specific elements.

    Args:
        element_ids: IDs of elements to highlight
        annotation_text: Optional annotation text
        duration: Scene duration
        emphasis_type: Type of emphasis animation
        dim_others: Whether to dim non-highlighted elements

    Returns:
        Configured highlight scene
    """
    scene = SceneConfig(
        type=SceneType.HIGHLIGHT,
        duration=duration,
        name="Highlight",
        highlight_elements=element_ids,
        highlight_text=annotation_text,
        annotation=annotation_text,
        narrative_role=NarrativeRole.CLIMAX,
        transition_out=TransitionStyle.FADE,
        transition_duration=0.3,
    )

    # Add emphasis animations for highlighted elements
    emphasis_type_map = {
        "pulse": AnimationType.PULSE,
        "glow": AnimationType.GLOW,
        "shake": AnimationType.SHAKE,
        "indicate": AnimationType.INDICATE,
    }

    anim_type = emphasis_type_map.get(emphasis_type, AnimationType.PULSE)

    for elem_id in element_ids:
        scene.add_animation(AnimationConfig(
            type=anim_type,
            target_id=elem_id,
            duration=0.6,
            easing=EasingType.THERE_AND_BACK,
            repeat=2,
        ))

    scene.params["dim_others"] = dim_others

    # Add annotation if provided
    if annotation_text:
        annotation_elem = AnnotationElement(
            id="highlight_annotation",
            text=annotation_text,
            position=Position(x=0, y=3.0),
            style=Style(text_color="#22D3EE", font_size=24),
        )
        scene.add_element(
            annotation_elem,
            entrance=AnimationConfig(
                type=AnimationType.FADE_IN,
                duration=0.4,
                target_id="highlight_annotation",
            ),
            enter_at=0.3,
        )

    return scene


def create_transition_scene(
    from_time: str,
    to_time: str,
    duration: float = 1.0,
    style: TransitionStyle = TransitionStyle.CROSSFADE,
    annotation: Optional[str] = None,
) -> SceneConfig:
    """
    Create a transition scene between time periods or views.

    Args:
        from_time: Starting time period
        to_time: Ending time period
        duration: Transition duration
        style: Transition visual style
        annotation: Optional text during transition

    Returns:
        Configured transition scene
    """
    scene = SceneConfig(
        type=SceneType.TRANSITION,
        duration=duration,
        name=f"Transition: {from_time} → {to_time}",
        time_range=(from_time, to_time),
        annotation=annotation,
        narrative_role=NarrativeRole.CONTEXT,
        transition_out=style,
        transition_duration=duration * 0.8,
    )

    if annotation:
        scene.params["show_annotation"] = True

    return scene


def create_conclusion_scene(
    title: Optional[str] = None,
    summary_stats: Optional[Dict[str, Any]] = None,
    duration: float = 3.0,
    call_to_action: Optional[str] = None,
    winner_element_id: Optional[str] = None,
) -> SceneConfig:
    """
    Create a conclusion scene with summary and optional call to action.

    Args:
        title: Conclusion title (e.g., "Final Results")
        summary_stats: Dictionary of summary statistics to display
        duration: Scene duration
        call_to_action: Optional CTA text
        winner_element_id: Element to emphasize as "winner"

    Returns:
        Configured conclusion scene
    """
    scene = SceneConfig(
        type=SceneType.CONCLUSION,
        duration=duration,
        name="Conclusion",
        title=title or "Final Results",
        narrative_role=NarrativeRole.RESOLUTION,
        transition_out=TransitionStyle.FADE,
        transition_duration=1.0,
    )

    if summary_stats:
        scene.params["summary_stats"] = summary_stats

    if call_to_action:
        scene.params["cta"] = call_to_action

    if winner_element_id:
        scene.highlight_elements = [winner_element_id]
        scene.add_animation(AnimationConfig(
            type=AnimationType.GLOW,
            target_id=winner_element_id,
            duration=1.0,
            intensity=1.5,
            easing=EasingType.THERE_AND_BACK,
        ))

    return scene


def create_pause_scene(
    duration: float = 1.0,
    annotation: Optional[str] = None,
) -> SceneConfig:
    """
    Create a pause scene for dramatic effect.

    Args:
        duration: Pause duration
        annotation: Optional text during pause

    Returns:
        Configured pause scene
    """
    return SceneConfig(
        type=SceneType.PAUSE,
        duration=duration,
        name="Pause",
        annotation=annotation,
        narrative_role=NarrativeRole.CLIMAX,
        transition_out=TransitionStyle.CUT,
    )


# =============================================================================
# STORY ARC HELPERS
# =============================================================================

def create_standard_story_arc(
    title: str,
    subtitle: Optional[str] = None,
    data_duration: float = 15.0,
    include_highlights: bool = True,
) -> List[SceneConfig]:
    """
    Create a standard story arc with intro, reveal, data, and conclusion.

    This is a template for the most common animation structure:
    1. Intro (hook)
    2. Reveal (context)
    3. Data animation (rising action)
    4. Optional highlights (climax)
    5. Conclusion (resolution)

    Args:
        title: Animation title
        subtitle: Optional subtitle
        data_duration: Duration of main data animation
        include_highlights: Whether to include highlight scenes

    Returns:
        List of scene configs forming the story arc
    """
    scenes = []

    # Act 1: Introduction
    scenes.append(create_intro_scene(
        title=title,
        subtitle=subtitle,
        duration=3.0,
        animation_style="fade",
    ))

    # Act 2: Data reveal and main animation
    scenes.append(create_reveal_scene(
        element_ids=[],  # Will be populated by template
        duration=2.0,
        style="stagger",
        with_time_display=True,
    ))

    scenes.append(create_data_scene(
        duration=data_duration,
        highlight_changes=include_highlights,
        show_annotations=include_highlights,
    ))

    # Act 3: Conclusion
    scenes.append(create_conclusion_scene(
        duration=3.0,
    ))

    return scenes


def create_comparison_story_arc(
    title: str,
    before_time: str,
    after_time: str,
    insight_text: Optional[str] = None,
) -> List[SceneConfig]:
    """
    Create a comparison story arc showing before/after.

    Structure:
    1. Intro
    2. Show "before" state
    3. Transition
    4. Show "after" state
    5. Highlight the difference
    6. Conclusion

    Args:
        title: Animation title
        before_time: Time period for "before"
        after_time: Time period for "after"
        insight_text: Text explaining the change

    Returns:
        List of scene configs
    """
    scenes = []

    scenes.append(create_intro_scene(
        title=title,
        duration=2.5,
    ))

    scenes.append(create_reveal_scene(
        element_ids=[],
        duration=2.0,
        with_time_display=True,
        time_value=before_time,
    ))

    scenes.append(create_pause_scene(duration=1.0))

    scenes.append(create_transition_scene(
        from_time=before_time,
        to_time=after_time,
        duration=1.5,
        style=TransitionStyle.MORPH,
    ))

    if insight_text:
        scenes.append(create_highlight_scene(
            element_ids=[],
            annotation_text=insight_text,
            duration=2.5,
        ))

    scenes.append(create_conclusion_scene(
        duration=2.5,
    ))

    return scenes


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Scenes Module Loaded Successfully")
    print(f"Available scene types: {len(SceneType)}")
    print(f"Available presets: {len(SCENE_PRESETS)}")

    # Test creating scenes
    intro = create_intro_scene(
        title="Top 10 Countries by GDP",
        subtitle="1950 - 2020",
        duration=3.0,
    )
    print(f"\nIntro scene: {intro.name}, {intro.duration}s")
    print(f"  Elements: {len(intro.elements)}")

    reveal = create_reveal_scene(
        element_ids=["bar_1", "bar_2", "bar_3"],
        duration=2.0,
        style="stagger",
    )
    print(f"\nReveal scene: {reveal.name}, {reveal.duration}s")

    data = create_data_scene(
        duration=15.0,
        time_start="1950",
        time_end="2020",
    )
    print(f"\nData scene: {data.name}, {data.duration}s")

    highlight = create_highlight_scene(
        element_ids=["bar_china"],
        annotation_text="China overtakes Japan!",
        duration=2.0,
    )
    print(f"\nHighlight scene: {highlight.name}, {highlight.duration}s")

    conclusion = create_conclusion_scene(
        title="Final Rankings",
        duration=3.0,
    )
    print(f"\nConclusion scene: {conclusion.name}, {conclusion.duration}s")

    # Test story arc
    arc = create_standard_story_arc(
        title="World GDP Rankings",
        subtitle="70 Years of Economic History",
        data_duration=20.0,
    )
    print(f"\nStandard story arc: {len(arc)} scenes")
    total = sum(s.total_duration for s in arc)
    print(f"  Total duration: {total:.1f}s")
