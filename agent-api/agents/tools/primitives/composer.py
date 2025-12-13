"""
Story Composer Module

This module orchestrates scenes into cohesive, narrative-driven animations.
The composer takes a story configuration and generates the complete animation
by coordinating scenes, transitions, and narrative flow.

Key Concepts:
- StoryConfig: The complete animation specification
- StoryBeat: A moment in the narrative with its timing
- NarrativeStyle: Pacing and tone presets
- StoryComposer: The main orchestrator

The composer handles:
1. Scene sequencing and timing
2. Element lifecycle (creation, animation, destruction)
3. Transition choreography
4. Narrative pacing and rhythm
5. Auto-generated insights and annotations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum, auto

from agents.tools.primitives.elements import (
    Element,
    ElementType,
    Position,
    Style,
    TitleElement,
    SubtitleElement,
    TimeDisplayElement,
    AnnotationElement,
)
from agents.tools.primitives.animations import (
    AnimationType,
    AnimationConfig,
    AnimationSequence,
    EasingType,
    Direction,
    create_animation,
    get_easing_code,
)
from agents.tools.primitives.scenes import (
    SceneType,
    SceneConfig,
    SceneElement,
    TransitionStyle,
    NarrativeRole,
    create_intro_scene,
    create_reveal_scene,
    create_data_scene,
    create_highlight_scene,
    create_conclusion_scene,
)


# =============================================================================
# ENUMS
# =============================================================================

class NarrativeStyle(Enum):
    """Pacing and tone presets for different use cases"""
    DOCUMENTARY = "documentary"      # Slower, more dramatic pauses
    EXPLAINER = "explainer"          # Clear, educational pacing
    SOCIAL_MEDIA = "social_media"    # Fast, punchy, attention-grabbing
    PRESENTATION = "presentation"    # Professional, measured
    CINEMATIC = "cinematic"          # Dramatic, with long builds
    QUICK_INSIGHT = "quick_insight"  # Very short, key takeaway only


class MusicSync(Enum):
    """How animation syncs with music (future feature)"""
    NONE = "none"
    BEAT = "beat"
    SECTION = "section"
    CUSTOM = "custom"


# =============================================================================
# STORY BEAT
# =============================================================================

@dataclass
class StoryBeat:
    """
    A single moment in the narrative timeline.

    Story beats represent significant moments that the viewer should
    notice or remember. They help structure the emotional arc.
    """
    time: float  # When this beat occurs (seconds from start)
    description: str  # What happens at this beat
    scene_index: int  # Which scene this belongs to

    # Beat characteristics
    intensity: float = 0.5  # 0 = subtle, 1 = dramatic
    role: NarrativeRole = NarrativeRole.CONTEXT

    # Optional associated elements/animations
    element_ids: List[str] = field(default_factory=list)
    annotation: Optional[str] = None

    # Data insight (for auto-generated beats)
    insight_type: Optional[str] = None  # "rank_change", "new_leader", "milestone", etc.
    insight_data: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# STORY CONFIG
# =============================================================================

@dataclass
class StoryConfig:
    """
    Complete configuration for a story-driven animation.

    This is the top-level specification that defines:
    - What the story is about (title, theme)
    - How it unfolds (scenes, beats)
    - How it looks (style, theme)
    - How it feels (pacing, narrative style)
    """
    # Content
    title: str = "Data Story"
    subtitle: Optional[str] = None
    description: Optional[str] = None

    # Scenes (in order)
    scenes: List[SceneConfig] = field(default_factory=list)

    # Story beats (auto-generated or manual)
    beats: List[StoryBeat] = field(default_factory=list)

    # Style
    theme: str = "youtube_dark"
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER

    # Pacing
    intro_duration: float = 3.0
    outro_duration: float = 2.0
    default_transition_duration: float = 0.5

    # Data
    data_source: Optional[str] = None  # CSV path
    time_column: Optional[str] = None

    # Auto features
    auto_insights: bool = True  # Auto-detect and highlight insights
    auto_annotations: bool = True  # Auto-generate annotations
    auto_pacing: bool = True  # Auto-adjust pacing based on data

    # Output
    target_duration: Optional[float] = None  # If set, scales pacing to fit
    fps: int = 60
    resolution: Tuple[int, int] = (1920, 1080)

    # Metadata
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def add_scene(self, scene: SceneConfig) -> "StoryConfig":
        """Add a scene to the story"""
        self.scenes.append(scene)
        return self

    def add_beat(self, beat: StoryBeat) -> "StoryConfig":
        """Add a story beat"""
        self.beats.append(beat)
        return self

    @property
    def total_duration(self) -> float:
        """Calculate total story duration"""
        return sum(s.total_duration for s in self.scenes)

    @property
    def scene_count(self) -> int:
        """Number of scenes"""
        return len(self.scenes)

    def get_scene_start_time(self, scene_index: int) -> float:
        """Get the start time of a scene"""
        if scene_index >= len(self.scenes):
            return self.total_duration
        return sum(s.total_duration for s in self.scenes[:scene_index])

    def get_scene_at_time(self, time: float) -> Tuple[int, SceneConfig]:
        """Get the scene active at a given time"""
        elapsed = 0.0
        for i, scene in enumerate(self.scenes):
            if elapsed + scene.total_duration > time:
                return i, scene
            elapsed += scene.total_duration
        return len(self.scenes) - 1, self.scenes[-1] if self.scenes else None


# =============================================================================
# NARRATIVE STYLE PRESETS
# =============================================================================

NARRATIVE_STYLE_PRESETS: Dict[NarrativeStyle, Dict[str, Any]] = {
    NarrativeStyle.DOCUMENTARY: {
        "intro_duration": 4.0,
        "outro_duration": 3.0,
        "pause_between_scenes": 0.5,
        "transition_duration": 0.8,
        "data_step_duration": 1.2,
        "highlight_duration": 2.5,
        "annotation_duration": 2.0,
        "easing": EasingType.SMOOTH,
    },
    NarrativeStyle.EXPLAINER: {
        "intro_duration": 3.0,
        "outro_duration": 2.5,
        "pause_between_scenes": 0.3,
        "transition_duration": 0.5,
        "data_step_duration": 0.8,
        "highlight_duration": 2.0,
        "annotation_duration": 1.5,
        "easing": EasingType.EASE_OUT_CUBIC,
    },
    NarrativeStyle.SOCIAL_MEDIA: {
        "intro_duration": 1.5,
        "outro_duration": 1.0,
        "pause_between_scenes": 0.1,
        "transition_duration": 0.3,
        "data_step_duration": 0.4,
        "highlight_duration": 1.0,
        "annotation_duration": 1.0,
        "easing": EasingType.EASE_OUT_CUBIC,
    },
    NarrativeStyle.PRESENTATION: {
        "intro_duration": 3.5,
        "outro_duration": 2.0,
        "pause_between_scenes": 0.4,
        "transition_duration": 0.6,
        "data_step_duration": 1.0,
        "highlight_duration": 2.0,
        "annotation_duration": 1.8,
        "easing": EasingType.SMOOTH,
    },
    NarrativeStyle.CINEMATIC: {
        "intro_duration": 5.0,
        "outro_duration": 4.0,
        "pause_between_scenes": 1.0,
        "transition_duration": 1.2,
        "data_step_duration": 1.5,
        "highlight_duration": 3.0,
        "annotation_duration": 2.5,
        "easing": EasingType.EASE_IN_OUT_CUBIC,
    },
    NarrativeStyle.QUICK_INSIGHT: {
        "intro_duration": 1.0,
        "outro_duration": 0.5,
        "pause_between_scenes": 0.0,
        "transition_duration": 0.2,
        "data_step_duration": 0.3,
        "highlight_duration": 0.8,
        "annotation_duration": 0.8,
        "easing": EasingType.EASE_OUT_CUBIC,
    },
}


# =============================================================================
# STORY COMPOSER
# =============================================================================

class StoryComposer:
    """
    The main orchestrator that composes scenes into a complete story.

    The composer:
    1. Takes a StoryConfig
    2. Processes scenes in order
    3. Manages element lifecycle
    4. Generates story beats
    5. Creates the final animation timeline
    """

    def __init__(self, config: StoryConfig):
        self.config = config
        self.timeline: List[Dict[str, Any]] = []
        self.active_elements: Dict[str, Element] = {}
        self.current_time: float = 0.0

        # Get narrative style preset
        self.style_preset = NARRATIVE_STYLE_PRESETS.get(
            config.narrative_style,
            NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
        )

    def compose(self) -> "StoryComposer":
        """
        Compose the complete story timeline.

        Returns self for chaining.
        """
        self.timeline = []
        self.current_time = 0.0

        for scene_index, scene in enumerate(self.config.scenes):
            self._process_scene(scene_index, scene)

        # Sort timeline by time
        self.timeline.sort(key=lambda x: x["time"])

        return self

    def _process_scene(self, index: int, scene: SceneConfig):
        """Process a single scene and add to timeline"""
        scene_start = self.current_time

        # Add scene marker
        self.timeline.append({
            "time": scene_start,
            "type": "scene_start",
            "scene_index": index,
            "scene_type": scene.type.name,
            "scene_name": scene.name,
            "duration": scene.duration,
        })

        # Process scene elements
        for scene_elem in scene.elements:
            # Element entrance
            enter_time = scene_start + scene_elem.enter_at
            self.timeline.append({
                "time": enter_time,
                "type": "element_enter",
                "element_id": scene_elem.element.id,
                "element_type": scene_elem.element.type.name,
                "animation": scene_elem.entrance,
            })
            self.active_elements[scene_elem.element.id] = scene_elem.element

            # Element emphasis (if any)
            if scene_elem.emphasis and scene_elem.emphasis_at is not None:
                self.timeline.append({
                    "time": scene_start + scene_elem.emphasis_at,
                    "type": "element_emphasis",
                    "element_id": scene_elem.element.id,
                    "animation": scene_elem.emphasis,
                })

            # Element exit (if not persisting)
            if not scene_elem.persist and scene_elem.exit:
                exit_time = scene_elem.exit_at or (scene.duration - 0.5)
                self.timeline.append({
                    "time": scene_start + exit_time,
                    "type": "element_exit",
                    "element_id": scene_elem.element.id,
                    "animation": scene_elem.exit,
                })

        # Process scene animations
        for anim in scene.animations:
            self.timeline.append({
                "time": scene_start + anim.delay,
                "type": "animation",
                "animation": anim,
                "target_id": anim.target_id,
            })

        # Process animation sequences
        for seq in scene.sequences:
            for anim in seq.animations:
                self.timeline.append({
                    "time": scene_start + anim.delay,
                    "type": "animation",
                    "animation": anim,
                    "target_id": anim.target_id,
                    "sequence_name": seq.name,
                })

        # Scene transition
        if index < len(self.config.scenes) - 1:
            transition_time = scene_start + scene.duration
            self.timeline.append({
                "time": transition_time,
                "type": "transition",
                "style": scene.transition_out.value,
                "duration": scene.transition_duration,
                "from_scene": index,
                "to_scene": index + 1,
            })

        # Update current time
        self.current_time = scene_start + scene.total_duration

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get the composed timeline"""
        return self.timeline

    def get_duration(self) -> float:
        """Get total story duration"""
        return self.current_time

    def get_elements_at_time(self, time: float) -> List[str]:
        """Get IDs of elements visible at a given time"""
        visible = set()

        for event in self.timeline:
            if event["time"] > time:
                break

            if event["type"] == "element_enter":
                visible.add(event["element_id"])
            elif event["type"] == "element_exit":
                visible.discard(event["element_id"])

        return list(visible)

    def generate_beats(self, data: Optional[Dict[str, Any]] = None) -> List[StoryBeat]:
        """
        Auto-generate story beats based on the timeline and data.

        Story beats mark significant moments:
        - Scene starts
        - Major data changes
        - Insights and milestones
        """
        beats = []

        # Add beat for each scene start
        for i, scene in enumerate(self.config.scenes):
            start_time = self.config.get_scene_start_time(i)
            beats.append(StoryBeat(
                time=start_time,
                description=f"Scene: {scene.name or scene.type.name}",
                scene_index=i,
                role=scene.narrative_role,
                intensity=0.7 if scene.type in [SceneType.INTRO, SceneType.CLIMAX] else 0.5,
            ))

        # If data is provided, analyze for insights
        if data and self.config.auto_insights:
            data_beats = self._analyze_data_for_beats(data)
            beats.extend(data_beats)

        # Sort by time
        beats.sort(key=lambda b: b.time)

        self.config.beats = beats
        return beats

    def _analyze_data_for_beats(self, data: Dict[str, Any]) -> List[StoryBeat]:
        """Analyze data to find significant moments worth highlighting"""
        beats = []

        # Look for rank changes (for bar race type)
        if "rankings" in data:
            rankings = data["rankings"]
            times = sorted(rankings.keys())

            prev_leader = None
            for t in times:
                ranking = rankings[t]
                if ranking:
                    current_leader = ranking[0] if isinstance(ranking[0], str) else ranking[0][0]

                    if prev_leader and current_leader != prev_leader:
                        # Leadership change!
                        beats.append(StoryBeat(
                            time=data.get("time_mapping", {}).get(t, 0),
                            description=f"{current_leader} takes the lead!",
                            scene_index=self._find_data_scene_index(),
                            role=NarrativeRole.CLIMAX,
                            intensity=0.9,
                            insight_type="new_leader",
                            insight_data={
                                "new_leader": current_leader,
                                "old_leader": prev_leader,
                                "time": t,
                            },
                        ))

                    prev_leader = current_leader

        return beats

    def _find_data_scene_index(self) -> int:
        """Find the index of the main DATA scene"""
        for i, scene in enumerate(self.config.scenes):
            if scene.type == SceneType.DATA:
                return i
        return 0

    def scale_to_duration(self, target_duration: float):
        """
        Scale all timing to fit a target duration.

        Useful for creating different length versions of the same story.
        """
        current_duration = self.get_duration()
        if current_duration == 0:
            return

        scale_factor = target_duration / current_duration

        # Scale scene durations
        for scene in self.config.scenes:
            scene.duration *= scale_factor
            scene.transition_duration *= scale_factor

        # Scale timeline events
        for event in self.timeline:
            event["time"] *= scale_factor
            if "duration" in event:
                event["duration"] *= scale_factor
            if "animation" in event and event["animation"]:
                event["animation"].duration *= scale_factor
                event["animation"].delay *= scale_factor

        self.current_time = target_duration


# =============================================================================
# CODE GENERATION
# =============================================================================

def generate_story_code(
    composer: StoryComposer,
    theme: str = "youtube_dark",
) -> str:
    """
    Generate Manim code from a composed story.

    This creates the complete Python code that can be run with Manim
    to produce the animation.

    Args:
        composer: A StoryComposer that has been composed
        theme: Visual theme to use

    Returns:
        Complete Manim Python code as a string
    """
    config = composer.config
    timeline = composer.get_timeline()

    # Build the code sections
    imports = '''
from manim import *
import math

# =============================================================================
# STORY-DRIVEN ANIMATION
# =============================================================================
'''

    # Story metadata
    metadata = f'''
# --- Story Configuration ---
STORY_TITLE = "{config.title}"
STORY_SUBTITLE = "{config.subtitle or ''}"
TOTAL_DURATION = {composer.get_duration():.2f}
SCENE_COUNT = {len(config.scenes)}
'''

    # Scene definitions
    scenes_code = "\n# --- Scenes ---\n"
    scenes_code += "SCENES = [\n"
    for i, scene in enumerate(config.scenes):
        scenes_code += f'    {{"index": {i}, "type": "{scene.type.name}", "name": "{scene.name or ""}", "duration": {scene.duration}}},\n'
    scenes_code += "]\n"

    # Timeline events (simplified)
    timeline_code = "\n# --- Timeline Events ---\n"
    timeline_code += f"# Total events: {len(timeline)}\n"

    # Main scene class
    scene_class = '''

class GenScene(Scene):
    """
    Story-driven animation scene.

    This scene is automatically generated from a StoryConfig.
    """

    def construct(self):
        # Set background
        self.camera.background_color = "#0F0F1A"

        # The actual animation code will be injected here
        # based on the story configuration

        self.wait(1.0)
'''

    return imports + metadata + scenes_code + timeline_code + scene_class


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_story(
    title: str,
    subtitle: Optional[str] = None,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    theme: str = "youtube_dark",
) -> StoryConfig:
    """
    Create a new story configuration.

    Args:
        title: Story title
        subtitle: Optional subtitle
        narrative_style: Pacing style
        theme: Visual theme

    Returns:
        StoryConfig ready for adding scenes
    """
    preset = NARRATIVE_STYLE_PRESETS.get(
        narrative_style,
        NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
    )

    return StoryConfig(
        title=title,
        subtitle=subtitle,
        narrative_style=narrative_style,
        theme=theme,
        intro_duration=preset["intro_duration"],
        outro_duration=preset["outro_duration"],
        default_transition_duration=preset["transition_duration"],
    )


def create_bar_race_story(
    title: str,
    subtitle: Optional[str] = None,
    data_duration: float = 15.0,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    include_intro: bool = True,
    include_conclusion: bool = True,
) -> StoryConfig:
    """
    Create a pre-configured story for bar race animations.

    Args:
        title: Story title
        subtitle: Optional subtitle
        data_duration: Duration of the main race animation
        narrative_style: Pacing style
        include_intro: Whether to include intro scene
        include_conclusion: Whether to include conclusion scene

    Returns:
        StoryConfig with bar race scenes
    """
    story = create_story(
        title=title,
        subtitle=subtitle,
        narrative_style=narrative_style,
    )

    preset = NARRATIVE_STYLE_PRESETS[narrative_style]

    if include_intro:
        story.add_scene(create_intro_scene(
            title=title,
            subtitle=subtitle,
            duration=preset["intro_duration"],
        ))

    # Reveal scene (bars appear)
    story.add_scene(create_reveal_scene(
        element_ids=[],  # Will be populated by template
        duration=2.0,
        style="stagger",
        with_time_display=True,
    ))

    # Main data race
    story.add_scene(create_data_scene(
        duration=data_duration,
        highlight_changes=True,
        show_annotations=True,
    ))

    if include_conclusion:
        story.add_scene(create_conclusion_scene(
            title="Final Rankings",
            duration=preset["outro_duration"],
        ))

    return story


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Story Composer Module Loaded Successfully")
    print(f"Available narrative styles: {len(NarrativeStyle)}")

    # Test creating a story
    story = create_bar_race_story(
        title="Top 10 Countries by GDP",
        subtitle="1950 - 2020",
        data_duration=15.0,
        narrative_style=NarrativeStyle.EXPLAINER,
    )

    print(f"\nCreated story: {story.title}")
    print(f"  Scenes: {story.scene_count}")
    print(f"  Narrative style: {story.narrative_style.value}")

    # Compose the story
    composer = StoryComposer(story)
    composer.compose()

    print(f"\nComposed timeline:")
    print(f"  Total duration: {composer.get_duration():.1f}s")
    print(f"  Timeline events: {len(composer.get_timeline())}")

    # Generate code
    code = generate_story_code(composer)
    print(f"\nGenerated code: {len(code)} characters")
