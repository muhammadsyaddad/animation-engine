"""
Code Generation Module

This module generates Manim Python code from the primitives system.
It converts Elements, Animations, and Scenes into executable Manim code
that produces beautiful, story-driven data animations.

The code generation is modular:
- generate_elements_code(): Creates Manim mobjects from Elements
- generate_animations_code(): Creates animation calls from AnimationConfigs
- generate_scenes_code(): Creates scene methods from SceneConfigs
- generate_primitives_code(): Creates the complete Manim scene
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from textwrap import indent, dedent

from agents.tools.primitives.elements import (
    Element,
    ElementType,
    Position,
    Style,
    Anchor,
    Direction,
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
    ElementGroup,
)
from agents.tools.primitives.animations import (
    AnimationType,
    AnimationConfig,
    AnimationSequence,
    EasingType,
    Direction as AnimDirection,
    get_easing_code,
)
from agents.tools.primitives.scenes import (
    SceneType,
    SceneConfig,
    SceneElement,
    TransitionStyle,
)


# =============================================================================
# HELPER CODE TEMPLATES
# =============================================================================

IMPORTS_TEMPLATE = '''
from manim import *
import math
from typing import Dict, List, Any, Optional
'''

HELPER_FUNCTIONS_TEMPLATE = '''
# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_number(value: float) -> str:
    """Format large numbers with K/M/B suffixes"""
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    elif abs(value) >= 100:
        return f"{value:.0f}"
    elif abs(value) >= 1:
        return f"{value:.1f}"
    else:
        return f"{value:.2f}"


def ease_out_cubic(t: float) -> float:
    """Smooth ease-out cubic function"""
    return 1 - pow(1 - t, 3)


def ease_in_out_cubic(t: float) -> float:
    """Smooth ease-in-out cubic function"""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b"""
    return a + (b - a) * t
'''

EASING_FUNCTIONS_TEMPLATE = '''
# =============================================================================
# EASING FUNCTIONS
# =============================================================================

# Custom easing functions for advanced animations
def ease_out_back(t: float) -> float:
    """Ease out with slight overshoot"""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def ease_out_elastic(t: float) -> float:
    """Elastic ease out"""
    if t == 0 or t == 1:
        return t
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1


def ease_out_bounce(t: float) -> float:
    """Bouncy ease out"""
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375
'''


# =============================================================================
# ELEMENT CODE GENERATION
# =============================================================================

def generate_element_code(element: Element, var_name: Optional[str] = None) -> str:
    """
    Generate Manim code to create a single element.

    Args:
        element: The element to generate code for
        var_name: Variable name to use (defaults to element.id)

    Returns:
        Manim code string
    """
    var_name = var_name or element.id.replace("-", "_").replace(" ", "_")

    if isinstance(element, BarElement):
        return _generate_bar_code(element, var_name)
    elif isinstance(element, BubbleElement):
        return _generate_bubble_code(element, var_name)
    elif isinstance(element, LineElement):
        return _generate_line_code(element, var_name)
    elif isinstance(element, LabelElement):
        return _generate_label_code(element, var_name)
    elif isinstance(element, TitleElement):
        return _generate_title_code(element, var_name)
    elif isinstance(element, SubtitleElement):
        return _generate_subtitle_code(element, var_name)
    elif isinstance(element, AnnotationElement):
        return _generate_annotation_code(element, var_name)
    elif isinstance(element, TimeDisplayElement):
        return _generate_time_display_code(element, var_name)
    elif isinstance(element, CardElement):
        return _generate_card_code(element, var_name)
    elif isinstance(element, ElementGroup):
        return _generate_group_code(element, var_name)
    else:
        # Generic element
        return f"# {var_name} = Element (type: {element.type.name})\n"


def _generate_bar_code(bar: BarElement, var_name: str) -> str:
    """Generate code for a bar element"""
    pos = bar.position
    style = bar.style

    fill_color = style.fill_color or "#6366F1"
    fill_opacity = style.fill_opacity
    corner_radius = style.corner_radius or 0.12

    code = f'''
# Bar: {bar.category or bar.id}
{var_name} = RoundedRectangle(
    corner_radius={corner_radius},
    width={bar.width},
    height={bar.height},
    fill_color="{fill_color}",
    fill_opacity={fill_opacity},
    stroke_width={style.stroke_width},
)
{var_name}.move_to([{pos.x}, {pos.y}, {pos.z}])
{var_name}_value = {bar.value}
{var_name}_category = "{bar.category}"
'''
    return code


def _generate_bubble_code(bubble: BubbleElement, var_name: str) -> str:
    """Generate code for a bubble element"""
    pos = bubble.position
    style = bubble.style

    fill_color = style.fill_color or "#6366F1"

    code = f'''
# Bubble: {bubble.entity or bubble.id}
{var_name} = Circle(
    radius={bubble.radius},
    fill_color="{fill_color}",
    fill_opacity={style.fill_opacity},
    stroke_width={style.stroke_width},
    stroke_color="{style.stroke_color or fill_color}",
)
{var_name}.move_to([{pos.x}, {pos.y}, {pos.z}])
{var_name}_value = {bubble.value}
'''

    if style.glow:
        glow_color = style.glow_color or fill_color
        code += f'''
{var_name}_glow = Circle(
    radius={bubble.radius + style.glow_radius},
    fill_color="{glow_color}",
    fill_opacity=0.3,
    stroke_width=0,
)
{var_name}_glow.move_to({var_name}.get_center())
'''

    return code


def _generate_line_code(line: LineElement, var_name: str) -> str:
    """Generate code for a line element"""
    style = line.style
    stroke_color = style.stroke_color or style.fill_color or "#22D3EE"

    # Convert points to Manim format
    points_str = ", ".join([f"[{p[0]}, {p[1]}, 0]" for p in line.points])

    code = f'''
# Line: {line.id}
{var_name}_points = [{points_str}]
{var_name} = VMobject()
{var_name}.set_points_smoothly({var_name}_points)
{var_name}.set_color("{stroke_color}")
{var_name}.set_stroke(width={line.line_width})
'''

    if line.area_fill:
        code += f'''
# Area fill under line
{var_name}_area_points = {var_name}_points.copy()
{var_name}_area_points.append([{var_name}_points[-1][0], 0, 0])
{var_name}_area_points.append([{var_name}_points[0][0], 0, 0])
{var_name}_area = Polygon(*{var_name}_area_points)
{var_name}_area.set_stroke(width=0)
{var_name}_area.set_fill("{stroke_color}", opacity={line.area_opacity})
'''

    return code


def _generate_label_code(label: LabelElement, var_name: str) -> str:
    """Generate code for a label element"""
    pos = label.position
    style = label.style

    text_color = style.text_color or "#FFFFFF"
    font_size = style.font_size or 18
    font_weight = "BOLD" if style.font_weight == "bold" else "NORMAL"

    # Handle value formatting
    if label.value is not None and label.format_type == "number":
        text_expr = f'format_number({label.value})'
        code = f'''
# Label: {label.id}
{var_name}_text = {label.prefix!r} + {text_expr} + {label.suffix!r}
{var_name} = Text(
    {var_name}_text,
    font_size={font_size},
    color="{text_color}",
    weight={font_weight},
)
{var_name}.move_to([{pos.x}, {pos.y}, {pos.z}])
'''
    else:
        code = f'''
# Label: {label.id}
{var_name} = Text(
    "{label.prefix}{label.text}{label.suffix}",
    font_size={font_size},
    color="{text_color}",
    weight={font_weight},
)
{var_name}.move_to([{pos.x}, {pos.y}, {pos.z}])
'''

    return code


def _generate_title_code(title: TitleElement, var_name: str) -> str:
    """Generate code for a title element"""
    pos = title.position
    style = title.style

    text_color = style.text_color or "#FFFFFF"
    font_size = style.font_size or 48

    code = f'''
# Title: {title.text[:30]}...
{var_name} = Text(
    "{title.text}",
    font_size={font_size},
    color="{text_color}",
    weight=BOLD,
)
{var_name}.move_to([{pos.x}, {pos.y}, {pos.z}])
'''
    return code


def _generate_subtitle_code(subtitle: SubtitleElement, var_name: str) -> str:
    """Generate code for a subtitle element"""
    pos = subtitle.position
    style = subtitle.style

    text_color = style.text_color or "#A1A1AA"
    font_size = style.font_size or 24

    code = f'''
# Subtitle: {subtitle.text[:30]}...
{var_name} = Text(
    "{subtitle.text}",
    font_size={font_size},
    color="{text_color}",
)
{var_name}.set_opacity({style.fill_opacity})
{var_name}.move_to([{pos.x}, {pos.y}, {pos.z}])
'''
    return code


def _generate_annotation_code(annotation: AnnotationElement, var_name: str) -> str:
    """Generate code for an annotation element"""
    pos = annotation.position
    style = annotation.style

    text_color = style.text_color or "#22D3EE"
    font_size = style.font_size or 20

    code = f'''
# Annotation: {annotation.text[:30]}...
{var_name}_text = Text(
    "{annotation.text}",
    font_size={font_size},
    color="{text_color}",
)
{var_name}_text.move_to([{pos.x}, {pos.y}, {pos.z}])
'''

    if annotation.bubble_style:
        code += f'''
{var_name}_bg = RoundedRectangle(
    corner_radius=0.15,
    width={var_name}_text.width + 0.4,
    height={var_name}_text.height + 0.3,
    fill_color="#1A1A2E",
    fill_opacity=0.95,
    stroke_color="{text_color}",
    stroke_width=2,
)
{var_name}_bg.move_to({var_name}_text.get_center())
{var_name} = VGroup({var_name}_bg, {var_name}_text)
'''
    else:
        code += f'{var_name} = {var_name}_text\n'

    if annotation.arrow and annotation.target_position:
        target = annotation.target_position
        code += f'''
{var_name}_arrow = Arrow(
    start=[{pos.x}, {pos.y}, 0],
    end=[{target.x}, {target.y}, 0],
    color="{annotation.arrow_color or text_color}",
    buff=0.2,
)
'''

    return code


def _generate_time_display_code(time_display: TimeDisplayElement, var_name: str) -> str:
    """Generate code for a time display element"""
    pos = time_display.position
    style = time_display.style

    text_color = style.text_color or "#A1A1AA"
    font_size = style.font_size or 72

    code = f'''
# Time Display
{var_name} = Text(
    "{time_display.time}",
    font_size={font_size},
    color="{text_color}",
    weight=BOLD,
)
{var_name}.set_opacity({style.fill_opacity})
'''

    if pos.x == 0 and pos.y == 0:
        # Default to bottom right corner
        code += f'{var_name}.to_corner(DR, buff=0.8)\n'
    else:
        code += f'{var_name}.move_to([{pos.x}, {pos.y}, {pos.z}])\n'

    return code


def _generate_card_code(card: CardElement, var_name: str) -> str:
    """Generate code for a card element"""
    pos = card.position
    style = card.style

    bg_color = style.fill_color or "#1A1A2E"
    text_color = style.text_color or "#FFFFFF"

    code = f'''
# Card: {card.title}
{var_name}_bg = RoundedRectangle(
    corner_radius=0.2,
    width={card.width},
    height={card.height},
    fill_color="{bg_color}",
    fill_opacity={style.fill_opacity},
    stroke_width=0,
)

{var_name}_title = Text(
    "{card.title}",
    font_size=16,
    color="{style.text_color or '#A1A1AA'}",
)

{var_name}_value = Text(
    "{card.prefix}" + format_number({card.value}) + "{card.suffix}",
    font_size=32,
    color="{text_color}",
    weight=BOLD,
)

{var_name}_title.next_to({var_name}_bg.get_top(), DOWN, buff=0.2)
{var_name}_value.move_to({var_name}_bg.get_center())
'''

    if card.change is not None:
        change_color = "#10B981" if card.change >= 0 else "#EF4444"
        change_sign = "+" if card.change >= 0 else ""
        code += f'''
{var_name}_change = Text(
    "{change_sign}{card.change:.1f}%",
    font_size=14,
    color="{change_color}",
)
{var_name}_change.next_to({var_name}_value, DOWN, buff=0.15)
{var_name} = VGroup({var_name}_bg, {var_name}_title, {var_name}_value, {var_name}_change)
'''
    else:
        code += f'{var_name} = VGroup({var_name}_bg, {var_name}_title, {var_name}_value)\n'

    code += f'{var_name}.move_to([{pos.x}, {pos.y}, {pos.z}])\n'

    return code


def _generate_group_code(group: ElementGroup, var_name: str) -> str:
    """Generate code for an element group"""
    code = f'# Group: {group.id}\n'

    child_vars = []
    for i, child in enumerate(group.children):
        child_var = f"{var_name}_child_{i}"
        code += generate_element_code(child, child_var)
        child_vars.append(child_var)

    children_str = ", ".join(child_vars)
    code += f'{var_name} = VGroup({children_str})\n'

    if group.position.x != 0 or group.position.y != 0:
        code += f'{var_name}.move_to([{group.position.x}, {group.position.y}, {group.position.z}])\n'

    return code


def generate_elements_code(elements: List[Element]) -> str:
    """
    Generate Manim code for multiple elements.

    Args:
        elements: List of elements to generate code for

    Returns:
        Combined Manim code string
    """
    code_parts = []
    for element in elements:
        code_parts.append(generate_element_code(element))
    return "\n".join(code_parts)


# =============================================================================
# ANIMATION CODE GENERATION
# =============================================================================

def generate_animation_code(
    animation: AnimationConfig,
    target_var: Optional[str] = None,
) -> str:
    """
    Generate Manim animation code from an AnimationConfig.

    Args:
        animation: The animation configuration
        target_var: Variable name of the target element

    Returns:
        Manim code string for the animation
    """
    target = target_var or (animation.target_id.replace("-", "_").replace(" ", "_") if animation.target_id else "element")
    duration = animation.duration
    easing = get_easing_code(animation.easing)

    anim_type = animation.type

    if anim_type == AnimationType.FADE_IN:
        return f'FadeIn({target}, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.FADE_OUT:
        return f'FadeOut({target}, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.GROW_FROM_CENTER:
        return f'GrowFromCenter({target}, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.GROW_FROM_EDGE:
        direction_map = {
            AnimDirection.UP: "DOWN",
            AnimDirection.DOWN: "UP",
            AnimDirection.LEFT: "RIGHT",
            AnimDirection.RIGHT: "LEFT",
        }
        edge = direction_map.get(animation.direction, "DOWN")
        return f'GrowFromEdge({target}, {edge}, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.SLIDE_IN:
        direction_map = {
            AnimDirection.UP: "DOWN",
            AnimDirection.DOWN: "UP",
            AnimDirection.LEFT: "RIGHT",
            AnimDirection.RIGHT: "LEFT",
        }
        edge = direction_map.get(animation.direction, "LEFT")
        return f'FadeIn({target}, shift={edge}*2, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.POP_IN:
        return f'GrowFromCenter({target}, run_time={duration}, rate_func=ease_out_back)'

    elif anim_type == AnimationType.TYPE_WRITER:
        return f'Write({target}, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.DRAW:
        return f'Create({target}, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.SHRINK_TO_CENTER:
        return f'ShrinkToCenter({target}, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.PULSE:
        scale = animation.scale_factor
        return f'''
# Pulse animation
{target}.animate.scale({scale}),
run_time={duration / 2},
rate_func=there_and_back,
'''

    elif anim_type == AnimationType.INDICATE:
        return f'Indicate({target}, scale_factor={animation.scale_factor}, run_time={duration})'

    elif anim_type == AnimationType.FLASH:
        return f'Flash({target}, run_time={duration})'

    elif anim_type == AnimationType.WIGGLE:
        return f'Wiggle({target}, run_time={duration})'

    elif anim_type == AnimationType.MORPH:
        # Morph requires a target state - return Transform placeholder
        return f'Transform({target}, {target}_new, run_time={duration}, rate_func={easing})'

    elif anim_type == AnimationType.MOVE_TO:
        if animation.to_value:
            pos = animation.to_value
            return f'{target}.animate.move_to([{pos[0]}, {pos[1]}, 0]), run_time={duration}, rate_func={easing}'
        return f'# MoveTo requires to_value parameter'

    elif anim_type == AnimationType.SCALE:
        return f'{target}.animate.scale({animation.scale_factor}), run_time={duration}, rate_func={easing}'

    elif anim_type == AnimationType.COLOR_SHIFT:
        if animation.to_color:
            return f'{target}.animate.set_color("{animation.to_color}"), run_time={duration}'
        return f'# ColorShift requires to_color parameter'

    elif anim_type == AnimationType.COUNT_UP or anim_type == AnimationType.COUNT_DOWN:
        # Count animation is complex - return a comment
        return f'# CountUp/Down animation for {target}: {animation.from_value} -> {animation.to_value}'

    elif anim_type == AnimationType.WAIT:
        return f'Wait({duration})'

    else:
        return f'# Animation {anim_type.name} for {target}'


def generate_animations_code(animations: List[AnimationConfig]) -> str:
    """
    Generate Manim code for multiple animations.

    Args:
        animations: List of animation configurations

    Returns:
        Combined Manim code string
    """
    code_parts = []
    for anim in animations:
        code_parts.append(generate_animation_code(anim))
    return "\n".join(code_parts)


def generate_animation_sequence_code(
    sequence: AnimationSequence,
    indent_level: int = 2,
) -> str:
    """
    Generate Manim code for an animation sequence.

    Args:
        sequence: The animation sequence
        indent_level: Indentation level

    Returns:
        Manim code string
    """
    indent_str = "    " * indent_level

    if sequence.mode == "parallel":
        # All animations play together
        anim_codes = [generate_animation_code(a) for a in sequence.animations]
        anims_str = f",\n{indent_str}".join(anim_codes)
        return f'''
{indent_str}self.play(
{indent_str}    {anims_str},
{indent_str})
'''

    elif sequence.mode == "sequence":
        # Animations play one after another
        code_parts = []
        for anim in sequence.animations:
            anim_code = generate_animation_code(anim)
            code_parts.append(f'{indent_str}self.play({anim_code})')
        return "\n".join(code_parts)

    else:  # stagger
        # Use LaggedStart
        anim_codes = [generate_animation_code(a) for a in sequence.animations]
        anims_str = f",\n{indent_str}        ".join(anim_codes)
        stagger = sequence.animations[0].stagger_delay if sequence.animations else 0.1
        return f'''
{indent_str}self.play(
{indent_str}    LaggedStart(
{indent_str}        {anims_str},
{indent_str}        lag_ratio={stagger},
{indent_str}    ),
{indent_str})
'''


# =============================================================================
# SCENE CODE GENERATION
# =============================================================================

def generate_scene_code(
    scene: SceneConfig,
    scene_index: int,
) -> str:
    """
    Generate Manim code for a scene.

    Args:
        scene: The scene configuration
        scene_index: Index of the scene for method naming

    Returns:
        Manim code string for the scene method
    """
    method_name = f"scene_{scene_index}_{scene.type.name.lower()}"

    code = f'''
    def {method_name}(self):
        """
        {scene.name or scene.type.name}
        Duration: {scene.duration}s
        """
'''

    # Generate element creation
    for scene_elem in scene.elements:
        elem = scene_elem.element
        elem_var = elem.id.replace("-", "_").replace(" ", "_")
        elem_code = generate_element_code(elem, elem_var)
        # Indent the element code
        elem_code_indented = indent(elem_code.strip(), "        ")
        code += elem_code_indented + "\n"

    # Generate entrance animations
    entrance_anims = []
    for scene_elem in scene.elements:
        if scene_elem.entrance:
            elem_var = scene_elem.element.id.replace("-", "_").replace(" ", "_")
            anim_code = generate_animation_code(scene_elem.entrance, elem_var)
            entrance_anims.append(anim_code)

    if entrance_anims:
        anims_str = ",\n            ".join(entrance_anims)
        code += f'''
        # Entrance animations
        self.play(
            {anims_str},
        )
'''

    # Generate scene animations
    for anim in scene.animations:
        anim_code = generate_animation_code(anim)
        code += f'        self.play({anim_code})\n'

    # Generate sequences
    for seq in scene.sequences:
        seq_code = generate_animation_sequence_code(seq, indent_level=2)
        code += seq_code

    # Add wait at end of scene
    remaining_time = scene.duration - sum(a.duration for a in scene.animations)
    if remaining_time > 0:
        code += f'\n        self.wait({remaining_time:.2f})\n'

    return code


def generate_scenes_code(scenes: List[SceneConfig]) -> str:
    """
    Generate Manim code for multiple scenes.

    Args:
        scenes: List of scene configurations

    Returns:
        Combined Manim code string
    """
    code_parts = []
    for i, scene in enumerate(scenes):
        code_parts.append(generate_scene_code(scene, i))
    return "\n".join(code_parts)


# =============================================================================
# MAIN GENERATION FUNCTION
# =============================================================================

def generate_primitives_code(
    elements: List[Element] = None,
    animations: List[AnimationConfig] = None,
    scenes: List[SceneConfig] = None,
    story_config: Any = None,  # StoryConfig
    theme: str = "youtube_dark",
    class_name: str = "GenScene",
) -> str:
    """
    Generate complete Manim code from primitives.

    This is the main entry point for code generation. It takes
    elements, animations, and scenes and produces a complete
    Manim Python file.

    Args:
        elements: List of elements to create
        animations: List of animations to apply
        scenes: List of scenes to render
        story_config: Optional StoryConfig for metadata
        theme: Visual theme name
        class_name: Name for the Manim scene class

    Returns:
        Complete Manim Python code as a string
    """
    elements = elements or []
    animations = animations or []
    scenes = scenes or []

    # Get theme colors (simplified for now)
    theme_colors = {
        "youtube_dark": {
            "background": "#0F0F1A",
            "text_primary": "#FFFFFF",
            "text_secondary": "#A1A1AA",
            "primary": "#6366F1",
            "accent": "#22D3EE",
        },
        "presentation": {
            "background": "#FFFFFF",
            "text_primary": "#1A1A2E",
            "text_secondary": "#6B7280",
            "primary": "#2563EB",
            "accent": "#7C3AED",
        },
        "neon_glow": {
            "background": "#0A0A0F",
            "text_primary": "#FFFFFF",
            "text_secondary": "#9CA3AF",
            "primary": "#22D3EE",
            "accent": "#A855F7",
        },
    }

    colors = theme_colors.get(theme, theme_colors["youtube_dark"])

    # Build the code
    code = IMPORTS_TEMPLATE
    code += HELPER_FUNCTIONS_TEMPLATE
    code += EASING_FUNCTIONS_TEMPLATE

    # Theme configuration
    code += f'''
# =============================================================================
# THEME CONFIGURATION
# =============================================================================

THEME = {{
    "background": "{colors['background']}",
    "text_primary": "{colors['text_primary']}",
    "text_secondary": "{colors['text_secondary']}",
    "primary": "{colors['primary']}",
    "accent": "{colors['accent']}",
}}
'''

    # Story metadata if provided
    if story_config:
        code += f'''
# =============================================================================
# STORY CONFIGURATION
# =============================================================================

STORY_TITLE = "{story_config.title}"
STORY_SUBTITLE = "{story_config.subtitle or ''}"
'''

    # Main scene class
    code += f'''
# =============================================================================
# MAIN SCENE
# =============================================================================

class {class_name}(Scene):
    """
    Generated animation scene using the primitives system.
    """

    def construct(self):
        # Set background
        self.camera.background_color = THEME["background"]
'''

    # Generate element creation code
    if elements:
        code += "\n        # --- Create Elements ---\n"
        for elem in elements:
            elem_code = generate_element_code(elem)
            code += indent(elem_code, "        ")

    # Generate scene methods if scenes provided
    if scenes:
        for i, scene in enumerate(scenes):
            scene_code = generate_scene_code(scene, i)
            code += scene_code

        # Call scene methods in construct
        code += "\n        # --- Run Scenes ---\n"
        for i, scene in enumerate(scenes):
            method_name = f"scene_{i}_{scene.type.name.lower()}"
            code += f"        self.{method_name}()\n"

    # Or just run animations
    elif animations:
        code += "\n        # --- Animations ---\n"
        for anim in animations:
            anim_code = generate_animation_code(anim)
            code += f"        self.play({anim_code})\n"

    # Default wait at end
    code += "\n        # Hold final frame\n"
    code += "        self.wait(2.0)\n"

    return code


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Code Generation Module Loaded Successfully")

    # Test element code generation
    from agents.tools.primitives.elements import create_bar, create_title

    bar = create_bar(
        id="bar_usa",
        category="USA",
        value=21000000000000,
        color="#6366F1",
        position=Position(x=-2, y=0),
    )

    title = create_title(
        text="Top 10 Countries by GDP",
        color="#FFFFFF",
    )

    print("\n--- Bar Element Code ---")
    print(generate_element_code(bar))

    print("\n--- Title Element Code ---")
    print(generate_element_code(title))

    # Test animation code generation
    fade_in = AnimationConfig(
        type=AnimationType.FADE_IN,
        target_id="bar_usa",
        duration=0.5,
    )

    print("\n--- Animation Code ---")
    print(generate_animation_code(fade_in))

    # Test full generation
    print("\n--- Full Generation ---")
    full_code = generate_primitives_code(
        elements=[bar, title],
        theme="youtube_dark",
    )
    print(f"Generated {len(full_code)} characters of code")
