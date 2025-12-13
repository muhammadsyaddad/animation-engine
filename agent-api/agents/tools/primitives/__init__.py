"""
Animation Primitives Module

This module provides the building blocks for creating story-driven data animations.
Instead of monolithic templates, animations are composed from:

1. **Elements** - Visual objects (bars, bubbles, labels, titles, annotations)
2. **Animations** - Reusable animation types (fade, grow, morph, emphasize)
3. **Scenes** - Story beats (intro, reveal, climax, conclusion)
4. **Composer** - Orchestrates scenes into a cohesive narrative

Usage:
    from agents.tools.primitives import (
        # Elements
        BarElement, LabelElement, TitleElement, AnnotationElement,
        # Animations
        AnimationType, AnimationConfig,
        # Scenes
        SceneType, SceneConfig,
        # Composer
        StoryComposer, StoryConfig,
        # Code generation
        generate_primitives_code,
    )

Example:
    story = StoryConfig(
        title="Top 10 Countries by GDP",
        subtitle="70 years of economic history",
        scenes=[
            SceneConfig(type=SceneType.INTRO, duration=2.0),
            SceneConfig(type=SceneType.REVEAL, duration=3.0, stagger=0.1),
            SceneConfig(type=SceneType.RACE, duration=15.0),
            SceneConfig(type=SceneType.CONCLUSION, duration=2.0),
        ]
    )
"""

from agents.tools.primitives.elements import (
    # Base
    Element,
    ElementType,
    Position,
    # Concrete elements
    BarElement,
    BubbleElement,
    LineElement,
    LabelElement,
    TitleElement,
    SubtitleElement,
    AnnotationElement,
    CalloutElement,
    TimeDisplayElement,
    LegendElement,
    AxisElement,
    CardElement,
    # Factories
    create_element,
)

from agents.tools.primitives.animations import (
    # Types
    AnimationType,
    EasingType,
    # Config
    AnimationConfig,
    AnimationSequence,
    # Presets
    ANIMATION_PRESETS,
    # Helpers
    create_animation,
    create_staggered_animation,
    create_emphasis_animation,
)

from agents.tools.primitives.scenes import (
    # Types
    SceneType,
    # Config
    SceneConfig,
    SceneElement,
    # Presets
    SCENE_PRESETS,
    # Builders
    create_intro_scene,
    create_reveal_scene,
    create_data_scene,
    create_highlight_scene,
    create_transition_scene,
    create_conclusion_scene,
)

from agents.tools.primitives.composer import (
    # Main composer
    StoryComposer,
    StoryConfig,
    StoryBeat,
    # Narrative helpers
    NarrativeStyle,
    # Generation
    generate_story_code,
)

# Convenience function to generate all primitives code for Manim
from agents.tools.primitives.codegen import (
    generate_primitives_code,
    generate_elements_code,
    generate_animations_code,
    generate_scenes_code,
)


__all__ = [
    # Elements
    "Element",
    "ElementType",
    "Position",
    "BarElement",
    "BubbleElement",
    "LineElement",
    "LabelElement",
    "TitleElement",
    "SubtitleElement",
    "AnnotationElement",
    "CalloutElement",
    "TimeDisplayElement",
    "LegendElement",
    "AxisElement",
    "CardElement",
    "create_element",
    # Animations
    "AnimationType",
    "EasingType",
    "AnimationConfig",
    "AnimationSequence",
    "ANIMATION_PRESETS",
    "create_animation",
    "create_staggered_animation",
    "create_emphasis_animation",
    # Scenes
    "SceneType",
    "SceneConfig",
    "SceneElement",
    "SCENE_PRESETS",
    "create_intro_scene",
    "create_reveal_scene",
    "create_data_scene",
    "create_highlight_scene",
    "create_transition_scene",
    "create_conclusion_scene",
    # Composer
    "StoryComposer",
    "StoryConfig",
    "StoryBeat",
    "NarrativeStyle",
    "generate_story_code",
    # Code generation
    "generate_primitives_code",
    "generate_elements_code",
    "generate_animations_code",
    "generate_scenes_code",
]
