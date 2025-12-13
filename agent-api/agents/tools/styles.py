"""
Modern Animation Styles Module

This module provides beautiful, cohesive design systems for data animations.
Includes color palettes, typography settings, animation timing presets,
and helper functions for creating polished visualizations.

Design Philosophy:
- YouTube/Presentation ready aesthetics
- Accessible color contrasts
- Smooth, professional animations
- Consistent visual language across chart types
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# =============================================================================
# COLOR PALETTES
# =============================================================================

class PaletteType(Enum):
    """Available color palette styles"""
    VIBRANT = "vibrant"          # Bold, YouTube-friendly
    CORPORATE = "corporate"       # Professional, presentation-ready
    PASTEL = "pastel"            # Soft, friendly
    NEON = "neon"                # Dark mode, high contrast
    EARTH = "earth"              # Natural, warm tones
    OCEAN = "ocean"              # Cool, calming blues
    SUNSET = "sunset"            # Warm gradients
    MONOCHROME = "monochrome"    # Elegant grayscale


@dataclass
class ColorPalette:
    """A cohesive color palette for animations"""
    name: str
    primary: str                  # Main accent color
    secondary: str                # Secondary accent
    background: str               # Scene background
    surface: str                  # Card/panel backgrounds
    text_primary: str             # Main text color
    text_secondary: str           # Subdued text
    text_on_primary: str          # Text on primary color
    accent: str                   # Highlight/emphasis
    success: str                  # Positive values
    warning: str                  # Caution/neutral
    error: str                    # Negative values
    chart_colors: List[str]       # Sequential colors for data series
    gradient_start: str           # For gradient effects
    gradient_end: str
    shadow_color: str             # For depth effects

    def get_chart_color(self, index: int) -> str:
        """Get chart color by index, cycling through palette"""
        return self.chart_colors[index % len(self.chart_colors)]

    def as_manim_config(self) -> str:
        """Generate Manim-compatible color configuration code"""
        return f'''
# Color Configuration
PALETTE = {{
    "primary": "{self.primary}",
    "secondary": "{self.secondary}",
    "background": "{self.background}",
    "surface": "{self.surface}",
    "text_primary": "{self.text_primary}",
    "text_secondary": "{self.text_secondary}",
    "text_on_primary": "{self.text_on_primary}",
    "accent": "{self.accent}",
    "success": "{self.success}",
    "warning": "{self.warning}",
    "error": "{self.error}",
    "gradient_start": "{self.gradient_start}",
    "gradient_end": "{self.gradient_end}",
    "shadow": "{self.shadow_color}",
}}
CHART_COLORS = {self.chart_colors}
'''


# Pre-defined palettes
PALETTES: Dict[PaletteType, ColorPalette] = {

    PaletteType.VIBRANT: ColorPalette(
        name="Vibrant",
        primary="#6366F1",           # Indigo
        secondary="#EC4899",          # Pink
        background="#0F0F1A",         # Deep navy black
        surface="#1A1A2E",            # Slightly lighter
        text_primary="#FFFFFF",
        text_secondary="#A1A1AA",
        text_on_primary="#FFFFFF",
        accent="#22D3EE",             # Cyan
        success="#10B981",            # Emerald
        warning="#F59E0B",            # Amber
        error="#EF4444",              # Red
        chart_colors=[
            "#6366F1",  # Indigo
            "#EC4899",  # Pink
            "#22D3EE",  # Cyan
            "#10B981",  # Emerald
            "#F59E0B",  # Amber
            "#8B5CF6",  # Purple
            "#F97316",  # Orange
            "#14B8A6",  # Teal
            "#EF4444",  # Red
            "#84CC16",  # Lime
            "#06B6D4",  # Sky
            "#D946EF",  # Fuchsia
        ],
        gradient_start="#6366F1",
        gradient_end="#EC4899",
        shadow_color="#00000066",
    ),

    PaletteType.CORPORATE: ColorPalette(
        name="Corporate",
        primary="#2563EB",            # Blue
        secondary="#0891B2",          # Cyan
        background="#FFFFFF",         # White
        surface="#F8FAFC",            # Slate 50
        text_primary="#1E293B",       # Slate 800
        text_secondary="#64748B",     # Slate 500
        text_on_primary="#FFFFFF",
        accent="#0EA5E9",             # Sky
        success="#059669",            # Emerald 600
        warning="#D97706",            # Amber 600
        error="#DC2626",              # Red 600
        chart_colors=[
            "#2563EB",  # Blue
            "#0891B2",  # Cyan
            "#059669",  # Emerald
            "#7C3AED",  # Violet
            "#DB2777",  # Pink
            "#EA580C",  # Orange
            "#4F46E5",  # Indigo
            "#0D9488",  # Teal
            "#9333EA",  # Purple
            "#65A30D",  # Lime
            "#0284C7",  # Sky
            "#BE185D",  # Pink 700
        ],
        gradient_start="#2563EB",
        gradient_end="#0891B2",
        shadow_color="#1E293B1A",
    ),

    PaletteType.PASTEL: ColorPalette(
        name="Pastel",
        primary="#A78BFA",            # Violet 400
        secondary="#F9A8D4",          # Pink 300
        background="#FEFCE8",         # Yellow 50
        surface="#FFFFFF",
        text_primary="#374151",       # Gray 700
        text_secondary="#6B7280",     # Gray 500
        text_on_primary="#1F2937",
        accent="#67E8F9",             # Cyan 300
        success="#86EFAC",            # Green 300
        warning="#FCD34D",            # Amber 300
        error="#FCA5A5",              # Red 300
        chart_colors=[
            "#A78BFA",  # Violet
            "#F9A8D4",  # Pink
            "#67E8F9",  # Cyan
            "#86EFAC",  # Green
            "#FCD34D",  # Amber
            "#C4B5FD",  # Violet lighter
            "#FBCFE8",  # Pink lighter
            "#A5F3FC",  # Cyan lighter
            "#BBF7D0",  # Green lighter
            "#FDE68A",  # Amber lighter
            "#DDD6FE",  # Violet 200
            "#F5D0FE",  # Fuchsia 200
        ],
        gradient_start="#A78BFA",
        gradient_end="#F9A8D4",
        shadow_color="#6B728033",
    ),

    PaletteType.NEON: ColorPalette(
        name="Neon",
        primary="#00FF88",            # Neon green
        secondary="#FF00FF",          # Magenta
        background="#000000",         # Pure black
        surface="#111111",
        text_primary="#FFFFFF",
        text_secondary="#888888",
        text_on_primary="#000000",
        accent="#00FFFF",             # Cyan
        success="#00FF88",            # Neon green
        warning="#FFFF00",            # Yellow
        error="#FF0055",              # Neon red
        chart_colors=[
            "#00FF88",  # Neon green
            "#FF00FF",  # Magenta
            "#00FFFF",  # Cyan
            "#FFFF00",  # Yellow
            "#FF6600",  # Orange
            "#FF0055",  # Red
            "#00AAFF",  # Blue
            "#AA00FF",  # Purple
            "#00FFAA",  # Mint
            "#FF00AA",  # Pink
            "#AAFF00",  # Lime
            "#00AAAA",  # Teal
        ],
        gradient_start="#00FF88",
        gradient_end="#00FFFF",
        shadow_color="#00FF8833",
    ),

    PaletteType.EARTH: ColorPalette(
        name="Earth",
        primary="#B45309",            # Amber 700
        secondary="#166534",          # Green 800
        background="#FEF3C7",         # Amber 100
        surface="#FFFBEB",            # Amber 50
        text_primary="#451A03",       # Amber 950
        text_secondary="#78350F",     # Amber 900
        text_on_primary="#FFFFFF",
        accent="#15803D",             # Green 700
        success="#16A34A",            # Green 600
        warning="#CA8A04",            # Yellow 600
        error="#B91C1C",              # Red 700
        chart_colors=[
            "#B45309",  # Amber
            "#166534",  # Green
            "#9A3412",  # Orange
            "#115E59",  # Teal
            "#854D0E",  # Yellow
            "#3F6212",  # Lime
            "#7C2D12",  # Orange dark
            "#14532D",  # Green dark
            "#A16207",  # Amber dark
            "#365314",  # Lime dark
            "#78350F",  # Amber 900
            "#1E3A2D",  # Green darker
        ],
        gradient_start="#B45309",
        gradient_end="#166534",
        shadow_color="#45180333",
    ),

    PaletteType.OCEAN: ColorPalette(
        name="Ocean",
        primary="#0077B6",            # Deep blue
        secondary="#00B4D8",          # Bright cyan
        background="#03045E",         # Navy
        surface="#023E8A",            # Dark blue
        text_primary="#CAF0F8",       # Light cyan
        text_secondary="#90E0EF",     # Medium cyan
        text_on_primary="#FFFFFF",
        accent="#48CAE4",             # Bright blue
        success="#06D6A0",            # Mint
        warning="#FFD166",            # Yellow
        error="#EF476F",              # Pink red
        chart_colors=[
            "#0077B6",  # Deep blue
            "#00B4D8",  # Cyan
            "#48CAE4",  # Light blue
            "#90E0EF",  # Lighter blue
            "#06D6A0",  # Mint
            "#FFD166",  # Yellow
            "#118AB2",  # Blue
            "#073B4C",  # Dark teal
            "#06A77D",  # Green
            "#EF476F",  # Pink
            "#00A8E8",  # Sky
            "#007EA7",  # Teal
        ],
        gradient_start="#0077B6",
        gradient_end="#00B4D8",
        shadow_color="#03045E66",
    ),

    PaletteType.SUNSET: ColorPalette(
        name="Sunset",
        primary="#F97316",            # Orange
        secondary="#E11D48",          # Rose
        background="#18181B",         # Zinc 900
        surface="#27272A",            # Zinc 800
        text_primary="#FAFAFA",       # Zinc 50
        text_secondary="#A1A1AA",     # Zinc 400
        text_on_primary="#FFFFFF",
        accent="#FACC15",             # Yellow
        success="#22C55E",            # Green
        warning="#FACC15",            # Yellow
        error="#EF4444",              # Red
        chart_colors=[
            "#F97316",  # Orange
            "#E11D48",  # Rose
            "#FACC15",  # Yellow
            "#FB7185",  # Pink
            "#FCD34D",  # Amber
            "#F43F5E",  # Rose light
            "#FB923C",  # Orange light
            "#FBBF24",  # Amber
            "#FDA4AF",  # Pink light
            "#FDE047",  # Yellow light
            "#FF6B6B",  # Coral
            "#FFE66D",  # Light yellow
        ],
        gradient_start="#F97316",
        gradient_end="#E11D48",
        shadow_color="#00000066",
    ),

    PaletteType.MONOCHROME: ColorPalette(
        name="Monochrome",
        primary="#3F3F46",            # Zinc 700
        secondary="#71717A",          # Zinc 500
        background="#FAFAFA",         # Zinc 50
        surface="#FFFFFF",
        text_primary="#18181B",       # Zinc 900
        text_secondary="#52525B",     # Zinc 600
        text_on_primary="#FFFFFF",
        accent="#27272A",             # Zinc 800
        success="#3F3F46",
        warning="#71717A",
        error="#18181B",
        chart_colors=[
            "#18181B",  # Zinc 900
            "#3F3F46",  # Zinc 700
            "#52525B",  # Zinc 600
            "#71717A",  # Zinc 500
            "#A1A1AA",  # Zinc 400
            "#D4D4D8",  # Zinc 300
            "#27272A",  # Zinc 800
            "#404040",  # Neutral 700
            "#525252",  # Neutral 600
            "#737373",  # Neutral 500
            "#A3A3A3",  # Neutral 400
            "#E5E5E5",  # Neutral 200
        ],
        gradient_start="#3F3F46",
        gradient_end="#71717A",
        shadow_color="#18181B1A",
    ),
}


def get_palette(palette_type: PaletteType = PaletteType.VIBRANT) -> ColorPalette:
    """Get a color palette by type"""
    return PALETTES.get(palette_type, PALETTES[PaletteType.VIBRANT])


def get_palette_by_name(name: str) -> ColorPalette:
    """Get a color palette by string name"""
    name_lower = name.lower()
    for pt in PaletteType:
        if pt.value == name_lower:
            return PALETTES[pt]
    return PALETTES[PaletteType.VIBRANT]


# =============================================================================
# TYPOGRAPHY
# =============================================================================

@dataclass
class Typography:
    """Typography configuration for consistent text styling"""
    # Font families (Manim uses system fonts)
    title_font: str = "Arial"
    body_font: str = "Arial"
    mono_font: str = "Courier New"

    # Font sizes (in Manim units, roughly equivalent to points)
    title_size: float = 48
    subtitle_size: float = 36
    heading_size: float = 28
    body_size: float = 22
    label_size: float = 18
    caption_size: float = 14

    # Font weights
    title_weight: str = "BOLD"
    subtitle_weight: str = "BOLD"
    heading_weight: str = "BOLD"
    body_weight: str = "NORMAL"
    label_weight: str = "NORMAL"

    # Line heights / spacing
    line_spacing: float = 1.2
    letter_spacing: float = 0.0

    def as_manim_config(self) -> str:
        """Generate Manim-compatible typography configuration"""
        return f'''
# Typography Configuration
TYPOGRAPHY = {{
    "title_size": {self.title_size},
    "subtitle_size": {self.subtitle_size},
    "heading_size": {self.heading_size},
    "body_size": {self.body_size},
    "label_size": {self.label_size},
    "caption_size": {self.caption_size},
}}
'''


# Pre-defined typography presets
TYPOGRAPHY_PRESETS: Dict[str, Typography] = {
    "default": Typography(),

    "youtube": Typography(
        title_size=56,
        subtitle_size=42,
        heading_size=32,
        body_size=26,
        label_size=22,
        caption_size=18,
    ),

    "presentation": Typography(
        title_size=52,
        subtitle_size=40,
        heading_size=30,
        body_size=24,
        label_size=20,
        caption_size=16,
    ),

    "compact": Typography(
        title_size=36,
        subtitle_size=28,
        heading_size=22,
        body_size=18,
        label_size=14,
        caption_size=12,
    ),
}


# =============================================================================
# ANIMATION TIMING
# =============================================================================

@dataclass
class AnimationTiming:
    """Timing configuration for smooth animations"""
    # Duration presets (in seconds)
    instant: float = 0.1
    fast: float = 0.3
    normal: float = 0.6
    slow: float = 1.0
    very_slow: float = 2.0

    # Specific animation durations
    intro_duration: float = 1.5
    outro_duration: float = 1.0
    transition_duration: float = 0.5
    data_update_duration: float = 0.8

    # Wait times
    pause_short: float = 0.5
    pause_medium: float = 1.0
    pause_long: float = 2.0

    # Stagger delays (for sequential animations)
    stagger_fast: float = 0.05
    stagger_normal: float = 0.1
    stagger_slow: float = 0.2

    # Rate functions (easing) - names match Manim's rate_func options
    default_ease: str = "smooth"          # Smooth ease in/out
    ease_in: str = "ease_in_sine"
    ease_out: str = "ease_out_sine"
    ease_in_out: str = "ease_in_out_sine"
    bounce: str = "ease_out_bounce"
    elastic: str = "ease_out_elastic"

    def as_manim_config(self) -> str:
        """Generate Manim-compatible timing configuration"""
        return f'''
# Timing Configuration
TIMING = {{
    "intro": {self.intro_duration},
    "outro": {self.outro_duration},
    "transition": {self.transition_duration},
    "data_update": {self.data_update_duration},
    "pause_short": {self.pause_short},
    "pause_medium": {self.pause_medium},
    "pause_long": {self.pause_long},
    "stagger": {self.stagger_normal},
}}
'''


# Pre-defined timing presets
TIMING_PRESETS: Dict[str, AnimationTiming] = {
    "default": AnimationTiming(),

    "fast": AnimationTiming(
        instant=0.05,
        fast=0.2,
        normal=0.4,
        slow=0.6,
        intro_duration=0.8,
        outro_duration=0.5,
        transition_duration=0.3,
        data_update_duration=0.5,
        pause_short=0.3,
        pause_medium=0.5,
        pause_long=1.0,
    ),

    "cinematic": AnimationTiming(
        instant=0.2,
        fast=0.5,
        normal=1.0,
        slow=1.5,
        very_slow=3.0,
        intro_duration=2.5,
        outro_duration=2.0,
        transition_duration=0.8,
        data_update_duration=1.2,
        pause_short=1.0,
        pause_medium=2.0,
        pause_long=3.0,
    ),

    "presentation": AnimationTiming(
        intro_duration=1.2,
        outro_duration=0.8,
        transition_duration=0.5,
        data_update_duration=0.8,
        pause_short=0.5,
        pause_medium=1.0,
        pause_long=1.5,
    ),
}


# =============================================================================
# VISUAL EFFECTS
# =============================================================================

@dataclass
class VisualEffects:
    """Configuration for visual polish effects"""
    # Shadows
    shadow_enabled: bool = True
    shadow_offset: Tuple[float, float] = (0.05, -0.05)
    shadow_blur: float = 0.1
    shadow_opacity: float = 0.3

    # Rounded corners (for bars, cards, etc.)
    corner_radius_small: float = 0.1
    corner_radius_medium: float = 0.2
    corner_radius_large: float = 0.3

    # Strokes
    stroke_width_thin: float = 1.0
    stroke_width_normal: float = 2.0
    stroke_width_thick: float = 4.0

    # Opacity levels
    opacity_subtle: float = 0.2
    opacity_medium: float = 0.5
    opacity_strong: float = 0.8
    opacity_full: float = 1.0

    # Glow effects
    glow_enabled: bool = True
    glow_radius: float = 0.15
    glow_opacity: float = 0.4

    # Background elements
    show_grid: bool = False
    grid_opacity: float = 0.1

    def as_manim_config(self) -> str:
        """Generate Manim-compatible effects configuration"""
        return f'''
# Visual Effects Configuration
EFFECTS = {{
    "shadow_enabled": {self.shadow_enabled},
    "shadow_offset": {self.shadow_offset},
    "shadow_opacity": {self.shadow_opacity},
    "corner_radius": {self.corner_radius_medium},
    "stroke_width": {self.stroke_width_normal},
    "glow_enabled": {self.glow_enabled},
    "glow_radius": {self.glow_radius},
    "glow_opacity": {self.glow_opacity},
}}
'''


# =============================================================================
# COMPLETE STYLE THEME
# =============================================================================

@dataclass
class AnimationStyle:
    """Complete animation style combining all design elements"""
    name: str
    palette: ColorPalette
    typography: Typography
    timing: AnimationTiming
    effects: VisualEffects

    # Additional style metadata
    description: str = ""
    recommended_for: List[str] = field(default_factory=list)

    def generate_manim_header(self) -> str:
        """Generate complete Manim configuration header"""
        return f'''
# =============================================================================
# STYLE: {self.name}
# {self.description}
# =============================================================================

{self.palette.as_manim_config()}
{self.typography.as_manim_config()}
{self.timing.as_manim_config()}
{self.effects.as_manim_config()}

# Helper function for consistent text creation
def styled_text(content, size_key="body", color=None, weight=None):
    """Create consistently styled text"""
    size = TYPOGRAPHY.get(size_key + "_size", TYPOGRAPHY["body_size"])
    text_color = color if color else PALETTE["text_primary"]
    return Text(str(content), font_size=size, color=text_color, weight=weight or NORMAL)

def styled_title(content):
    """Create a styled title"""
    return Text(str(content), font_size=TYPOGRAPHY["title_size"], color=PALETTE["text_primary"], weight=BOLD)

def styled_label(content, color=None):
    """Create a styled label"""
    return Text(str(content), font_size=TYPOGRAPHY["label_size"], color=color or PALETTE["text_secondary"])

def get_chart_color(index):
    """Get chart color by index"""
    return CHART_COLORS[index % len(CHART_COLORS)]
'''


# Pre-defined complete themes
THEMES: Dict[str, AnimationStyle] = {

    "youtube_dark": AnimationStyle(
        name="YouTube Dark",
        palette=PALETTES[PaletteType.VIBRANT],
        typography=TYPOGRAPHY_PRESETS["youtube"],
        timing=TIMING_PRESETS["default"],
        effects=VisualEffects(
            shadow_enabled=True,
            glow_enabled=True,
            corner_radius_medium=0.2,
        ),
        description="Bold, vibrant style perfect for YouTube videos",
        recommended_for=["bar_race", "line_evolution", "bubble"],
    ),

    "presentation": AnimationStyle(
        name="Presentation",
        palette=PALETTES[PaletteType.CORPORATE],
        typography=TYPOGRAPHY_PRESETS["presentation"],
        timing=TIMING_PRESETS["presentation"],
        effects=VisualEffects(
            shadow_enabled=True,
            shadow_opacity=0.15,
            glow_enabled=False,
            corner_radius_medium=0.15,
        ),
        description="Clean, professional style for business presentations",
        recommended_for=["bar_race", "line_evolution", "distribution"],
    ),

    "neon_glow": AnimationStyle(
        name="Neon Glow",
        palette=PALETTES[PaletteType.NEON],
        typography=TYPOGRAPHY_PRESETS["youtube"],
        timing=TIMING_PRESETS["fast"],
        effects=VisualEffects(
            shadow_enabled=False,
            glow_enabled=True,
            glow_radius=0.2,
            glow_opacity=0.6,
            corner_radius_medium=0.15,
        ),
        description="High-contrast neon style for dark themes",
        recommended_for=["line_evolution", "bubble"],
    ),

    "ocean_calm": AnimationStyle(
        name="Ocean Calm",
        palette=PALETTES[PaletteType.OCEAN],
        typography=TYPOGRAPHY_PRESETS["default"],
        timing=TIMING_PRESETS["cinematic"],
        effects=VisualEffects(
            shadow_enabled=True,
            glow_enabled=True,
            glow_opacity=0.3,
        ),
        description="Calming ocean theme with smooth animations",
        recommended_for=["line_evolution", "bubble", "distribution"],
    ),

    "sunset_energy": AnimationStyle(
        name="Sunset Energy",
        palette=PALETTES[PaletteType.SUNSET],
        typography=TYPOGRAPHY_PRESETS["youtube"],
        timing=TIMING_PRESETS["fast"],
        effects=VisualEffects(
            shadow_enabled=True,
            glow_enabled=True,
        ),
        description="Warm, energetic sunset colors",
        recommended_for=["bar_race", "bubble"],
    ),

    "minimal_light": AnimationStyle(
        name="Minimal Light",
        palette=PALETTES[PaletteType.MONOCHROME],
        typography=TYPOGRAPHY_PRESETS["presentation"],
        timing=TIMING_PRESETS["presentation"],
        effects=VisualEffects(
            shadow_enabled=True,
            shadow_opacity=0.1,
            glow_enabled=False,
            corner_radius_medium=0.1,
        ),
        description="Clean monochrome style for minimalist aesthetics",
        recommended_for=["line_evolution", "distribution"],
    ),

    "pastel_soft": AnimationStyle(
        name="Pastel Soft",
        palette=PALETTES[PaletteType.PASTEL],
        typography=TYPOGRAPHY_PRESETS["default"],
        timing=TIMING_PRESETS["default"],
        effects=VisualEffects(
            shadow_enabled=True,
            shadow_opacity=0.2,
            glow_enabled=False,
            corner_radius_medium=0.25,
        ),
        description="Soft pastel colors for friendly visualizations",
        recommended_for=["bubble", "distribution", "bento_grid"],
    ),
}


def get_theme(name: str = "youtube_dark") -> AnimationStyle:
    """Get a complete animation theme by name"""
    return THEMES.get(name, THEMES["youtube_dark"])


def list_themes() -> List[str]:
    """List all available theme names"""
    return list(THEMES.keys())


def list_palettes() -> List[str]:
    """List all available palette names"""
    return [pt.value for pt in PaletteType]


# =============================================================================
# MANIM CODE GENERATION HELPERS
# =============================================================================

def generate_easing_functions() -> str:
    """Generate smooth easing function definitions for Manim"""
    return '''
# Smooth easing functions
def ease_in_out_cubic(t):
    """Smooth cubic ease in/out"""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2

def ease_out_back(t):
    """Ease out with slight overshoot"""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)

def ease_out_elastic(t):
    """Elastic bounce at the end"""
    if t == 0 or t == 1:
        return t
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1
'''


def generate_helper_mobjects(palette: ColorPalette) -> str:
    """Generate helper Mobject creation functions"""
    return f'''
# Helper Mobject creators
def create_rounded_bar(width, height, color, corner_radius=0.15):
    """Create a styled rounded rectangle bar"""
    bar = RoundedRectangle(
        corner_radius=corner_radius,
        width=max(0.01, width),
        height=height,
        fill_color=color,
        fill_opacity=0.9,
        stroke_width=0,
    )
    return bar

def create_glow_dot(position, color, radius=0.08, glow_radius=0.15, glow_opacity=0.4):
    """Create a dot with glow effect"""
    glow = Dot(point=position, radius=glow_radius, color=color)
    glow.set_opacity(glow_opacity)
    dot = Dot(point=position, radius=radius, color=WHITE)
    return VGroup(glow, dot)

def create_value_label(value, position, color="{palette.text_primary}", font_size=22):
    """Create an animated value label with background"""
    label = DecimalNumber(value, num_decimal_places=0, font_size=font_size, color=color)
    label.add_background_rectangle(color="{palette.surface}", opacity=0.8, buff=0.1)
    label.move_to(position)
    return label

def create_category_label(text, color="{palette.text_primary}", font_size=20):
    """Create a styled category label"""
    return Text(str(text), font_size=font_size, color=color, weight=BOLD)

def create_time_display(time_value, corner=DR, font_size=72):
    """Create a large time/year display in corner"""
    label = Text(str(time_value), font_size=font_size, weight=BOLD, color="{palette.text_secondary}")
    label.to_corner(corner, buff=1.0)
    return label
'''


def generate_animation_helpers() -> str:
    """Generate animation helper functions"""
    return '''
# Animation helpers
def smooth_count_animation(decimal_mob, target_value, run_time=0.5):
    """Animate a DecimalNumber to a target value smoothly"""
    return decimal_mob.animate.set_value(target_value)

def staggered_fade_in(mobjects, lag_ratio=0.1, run_time=1.0):
    """Fade in multiple mobjects with stagger"""
    return LaggedStart(
        *[FadeIn(mob, shift=UP * 0.2) for mob in mobjects],
        lag_ratio=lag_ratio,
        run_time=run_time
    )

def smooth_transform_bars(old_bars, new_bars, run_time=0.8):
    """Smoothly transform bar positions and sizes"""
    return AnimationGroup(
        *[Transform(old, new) for old, new in zip(old_bars, new_bars)],
        run_time=run_time,
        rate_func=smooth
    )
'''


# =============================================================================
# DEFAULT EXPORTS
# =============================================================================

# Default theme for quick access
DEFAULT_THEME = THEMES["youtube_dark"]
DEFAULT_PALETTE = PALETTES[PaletteType.VIBRANT]
DEFAULT_TYPOGRAPHY = TYPOGRAPHY_PRESETS["default"]
DEFAULT_TIMING = TIMING_PRESETS["default"]
DEFAULT_EFFECTS = VisualEffects()
