"""
Modern Animation Templates Module

This package provides beautiful, production-ready animation templates
for various chart types. Each template is designed to create
YouTube/presentation-quality animations with:

- Modern color palettes
- Smooth easing animations
- Clean typography
- Configurable styling
- Professional visual polish
- Story-driven narrative structure

Available Templates:
- bar_race: Story-driven bar chart race animations (rankings over time)
- line_evolution: Dynamic line chart animations (trends over time)
- distribution: Histogram/distribution animations over time
- bubble_chart: Bubble chart animations (multi-dimensional data over time)
- bento_grid: KPI dashboard grid animations

Usage:
    from agents.tools.templates import generate_bar_race, generate_line_evolution, generate_distribution, generate_bubble_chart, generate_bento_grid

    # Bar race with story-driven narrative
    code = generate_bar_race(spec, csv_path, theme="youtube_dark")

    # With custom narrative style
    from agents.tools.templates import NarrativeStyle
    code = generate_bar_race(
        spec, csv_path,
        theme="youtube_dark",
        narrative_style=NarrativeStyle.CINEMATIC,
        include_intro=True,
        include_conclusion=True,
        auto_highlights=True,
    )

    # Other templates
    code = generate_line_evolution(spec, csv_path, theme="neon_glow")
    code = generate_distribution(spec, csv_path, theme="youtube_dark")
    code = generate_bubble_chart(spec, csv_path, theme="ocean_calm")
    code = generate_bento_grid(spec, csv_path, theme="youtube_dark")
"""

# Bar Race (Story-Driven with Primitives)
from agents.tools.templates.bar_race import (
    generate_bar_race,
    parse_csv_data as parse_bar_race_data,
    BarRaceData,
    BarRaceInsight,
    RankChange,
    detect_insights as detect_bar_race_insights,
    create_bar_race_story_config,
)

# Line Evolution (Story-Driven with Primitives)
from agents.tools.templates.line_evolution import (
    generate_line_evolution,
    parse_csv_data as parse_line_evolution_data,
    LineEvolutionData,
    LineInsight,
    detect_insights as detect_line_insights,
    create_line_evolution_story_config,
)

# Distribution (Story-Driven with Primitives)
from agents.tools.templates.distribution import (
    generate_distribution,
    generate_distribution_code,  # Alias for backward compatibility
    parse_csv_data as parse_distribution_data,
    DistributionData,
    DistributionInsight,
    detect_insights as detect_distribution_insights,
    create_distribution_story_config,
    format_number,
    format_range_label,
)

# Bubble Chart (Story-Driven with Primitives)
from agents.tools.templates.bubble_chart import (
    generate_bubble_chart,
    generate_bubble_code,  # Alias for backward compatibility
    parse_csv_data as parse_bubble_chart_data,
    BubbleChartData,
    BubbleInsight,
    detect_insights as detect_bubble_insights,
    create_bubble_chart_story_config,
    format_number as format_bubble_number,
    format_axis_value,
)

# Bento Grid (Story-Driven with Primitives)
from agents.tools.templates.bento_grid import (
    generate_bento_grid,
    generate_bento_grid_code,  # Alias for backward compatibility
    parse_csv_data as parse_bento_grid_data,
    BentoGridData,
    BentoInsight,
    detect_insights as detect_bento_insights,
    create_bento_grid_story_config,
    KPIItem,
    format_number as format_bento_number,
    format_percentage,
    format_currency,
)

# Count Bar (Simple horizontal bar chart for categorical-only data)
from agents.tools.templates.count_bar import (
    generate_count_bar,
    parse_csv_data as parse_count_bar_data,
    CountBarData,
    CountBarInsight,
    detect_insights as detect_count_bar_insights,
    create_count_bar_story_config,
    format_count,
    transform_count_by_column,
)

# Single Numeric (Bar chart for datasets with one numeric column)
from agents.tools.templates.single_numeric import (
    generate_single_numeric,
    parse_csv_data as parse_single_numeric_data,
    SingleNumericData,
    SingleNumericInsight,
    detect_insights as detect_single_numeric_insights,
    create_single_numeric_story_config,
    format_value as format_single_numeric_value,
)

# Primitives - Composer
from agents.tools.primitives.composer import (
    NarrativeStyle,
    StoryConfig,
    StoryComposer,
    StoryBeat,
    create_bar_race_story,
)

# Primitives - Scenes
from agents.tools.primitives.scenes import (
    SceneType,
    SceneConfig,
    TransitionStyle,
    NarrativeRole,
    create_intro_scene,
    create_reveal_scene,
    create_data_scene,
    create_highlight_scene,
    create_conclusion_scene,
)

# Primitives - Animations
from agents.tools.primitives.animations import (
    AnimationType,
    AnimationConfig,
    AnimationSequence,
    EasingType,
    ANIMATION_PRESETS,
    create_animation,
    create_staggered_animation,
)

# Primitives - Elements
from agents.tools.primitives.elements import (
    ElementType,
    Position,
    Style,
    BarElement,
    TitleElement,
    AnnotationElement,
)


# Template registry for dynamic access
TEMPLATE_REGISTRY = {
    "bar_race": generate_bar_race,
    "line_evolution": generate_line_evolution,
    "distribution": generate_distribution,
    "bubble_chart": generate_bubble_chart,
    "bento_grid": generate_bento_grid,
    "count_bar": generate_count_bar,
    "single_numeric": generate_single_numeric,
}


def get_template(template_name: str):
    """
    Get a template generator function by name.

    Args:
        template_name: Name of the template (e.g., "bar_race", "line_evolution", etc.)

    Returns:
        Template generator function

    Raises:
        KeyError: If template not found
    """
    if template_name not in TEMPLATE_REGISTRY:
        available = ", ".join(TEMPLATE_REGISTRY.keys())
        raise KeyError(f"Template '{template_name}' not found. Available: {available}")
    return TEMPLATE_REGISTRY[template_name]


def list_templates() -> list:
    """List all available template names"""
    return list(TEMPLATE_REGISTRY.keys())


def list_narrative_styles() -> list:
    """List available narrative styles for story-driven templates"""
    return [style.value for style in NarrativeStyle]


def list_story_config_creators() -> dict:
    """List all story config creator functions by template name"""
    return {
        "bar_race": create_bar_race_story_config,
        "line_evolution": create_line_evolution_story_config,
        "distribution": create_distribution_story_config,
        "bubble_chart": create_bubble_chart_story_config,
        "bento_grid": create_bento_grid_story_config,
        "count_bar": create_count_bar_story_config,
        "single_numeric": create_single_numeric_story_config,
    }


__all__ = [
    # Bar Race
    "generate_bar_race",
    "parse_bar_race_data",
    "BarRaceData",
    "BarRaceInsight",
    "RankChange",
    "detect_bar_race_insights",
    "create_bar_race_story_config",
    # Line Evolution
    "generate_line_evolution",
    "parse_line_evolution_data",
    "LineEvolutionData",
    "LineInsight",
    "detect_line_insights",
    "create_line_evolution_story_config",
    # Distribution
    "generate_distribution",
    "generate_distribution_code",
    "parse_distribution_data",
    "DistributionData",
    "DistributionInsight",
    "detect_distribution_insights",
    "create_distribution_story_config",
    "format_number",
    "format_range_label",
    # Bubble Chart
    "generate_bubble_chart",
    "generate_bubble_code",
    "parse_bubble_chart_data",
    "BubbleChartData",
    "BubbleInsight",
    "detect_bubble_insights",
    "create_bubble_chart_story_config",
    "format_axis_value",
    # Bento Grid
    "generate_bento_grid",
    "generate_bento_grid_code",
    "parse_bento_grid_data",
    "BentoGridData",
    "BentoInsight",
    "detect_bento_insights",
    "create_bento_grid_story_config",
    "KPIItem",
    "format_percentage",
    "format_currency",
    # Count Bar
    "generate_count_bar",
    "parse_count_bar_data",
    "CountBarData",
    "CountBarInsight",
    "detect_count_bar_insights",
    "create_count_bar_story_config",
    "format_count",
    "transform_count_by_column",
    # Single Numeric
    "generate_single_numeric",
    "parse_single_numeric_data",
    "SingleNumericData",
    "SingleNumericInsight",
    "detect_single_numeric_insights",
    "create_single_numeric_story_config",
    "format_single_numeric_value",
    # Primitives - Composer
    "NarrativeStyle",
    "StoryConfig",
    "StoryComposer",
    "StoryBeat",
    "create_bar_race_story",
    # Primitives - Scenes
    "SceneType",
    "SceneConfig",
    "TransitionStyle",
    "NarrativeRole",
    "create_intro_scene",
    "create_reveal_scene",
    "create_data_scene",
    "create_highlight_scene",
    "create_conclusion_scene",
    # Primitives - Animations
    "AnimationType",
    "AnimationConfig",
    "AnimationSequence",
    "EasingType",
    "ANIMATION_PRESETS",
    "create_animation",
    "create_staggered_animation",
    # Primitives - Elements
    "ElementType",
    "Position",
    "Style",
    "BarElement",
    "TitleElement",
    "AnnotationElement",
    # Registry
    "TEMPLATE_REGISTRY",
    "get_template",
    "list_templates",
    "list_narrative_styles",
    "list_story_config_creators",
]
