"""
Generate preview GIFs for all animation templates.

This script:
1. Creates sample datasets for each template
2. Generates Manim code using the template generators
3. Renders the code to video
4. Converts video to optimized GIF
5. Saves GIFs to the artifacts/previews directory

Usage:
    python -m scripts.previews.generate_previews [--template TEMPLATE_ID]

Requirements:
    - Manim Community Edition installed
    - ffmpeg installed (for GIF conversion)
    - PIL/Pillow for GIF optimization (optional)
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.previews.sample_data import create_all_sample_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

def get_artifacts_dir() -> Path:
    """Get the artifacts directory, handling both local and Docker environments."""
    # Try relative to this file first
    file_based = Path(__file__).parent.parent.parent / "artifacts"
    if file_based.exists():
        return file_based

    # Fall back to working directory (for Docker)
    cwd_based = Path(os.getcwd()) / "artifacts"
    cwd_based.mkdir(parents=True, exist_ok=True)
    return cwd_based


def get_previews_output_dir() -> Path:
    """Get the previews output directory, creating it if necessary."""
    previews_dir = get_artifacts_dir() / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    return previews_dir


# Legacy constants for backward compatibility
ARTIFACTS_DIR = get_artifacts_dir()
PREVIEWS_OUTPUT_DIR = get_previews_output_dir()

# GIF settings
GIF_WIDTH = 480  # Width in pixels (height auto-calculated for aspect ratio)
GIF_FPS = 12     # Frames per second for GIF
GIF_DURATION = 5  # Target duration in seconds (will trim/speed up if needed)

# Manim settings
MANIM_QUALITY = "low"  # low, medium, high
MANIM_FPS = 24


# ─────────────────────────────────────────────────────────────────────────────
# Data Binding Specs
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DataBinding:
    """Mock DataBinding for template generators."""
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    r_col: Optional[str] = None
    value_col: Optional[str] = None
    time_col: Optional[str] = None
    group_col: Optional[str] = None
    entity_col: Optional[str] = None
    label_col: Optional[str] = None
    change_col: Optional[str] = None
    category_col: Optional[str] = None


@dataclass
class ChartSpec:
    """Mock ChartSpec for template generators."""
    chart_type: str = "bubble"
    data_binding: DataBinding = field(default_factory=DataBinding)
    axes: Any = None
    creation_mode: int = 2
    style: Any = None
    timing: Any = None


# ─────────────────────────────────────────────────────────────────────────────
# Template Configurations
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "bar_race": {
        "generator": "generate_bar_race_code",
        "binding": DataBinding(
            entity_col="Brand",
            value_col="MarketShare",
            time_col="Year",
            group_col="Region",
        ),
        "chart_type": "bar_race",
    },
    "bubble": {
        "generator": "generate_bubble_code",
        "binding": DataBinding(
            x_col="GDP",
            y_col="LifeExpectancy",
            r_col="Population",
            time_col="Year",
            entity_col="Country",
            group_col="Continent",
        ),
        "chart_type": "bubble",
    },
    "line_evolution": {
        "generator": "generate_line_evolution_code",
        "binding": DataBinding(
            value_col="Price",
            time_col="Date",
            entity_col="Company",
        ),
        "chart_type": "line_evolution",
    },
    "distribution": {
        "generator": "generate_distribution_code",
        "binding": DataBinding(
            value_col="Score",
            time_col="Year",
            entity_col="Student",
        ),
        "chart_type": "distribution",
    },
    "bento_grid": {
        "generator": "generate_bento_grid_code",
        "binding": DataBinding(
            label_col="Metric",
            value_col="Value",
            change_col="Change",
        ),
        "chart_type": "bento_grid",
    },
    "count_bar": {
        "generator": "generate_count_bar_code",
        "binding": DataBinding(
            category_col="Category",
        ),
        "chart_type": "count_bar",
    },
    "single_numeric": {
        "generator": "generate_single_numeric_code",
        "binding": DataBinding(
            category_col="Region",
            value_col="Sales",
        ),
        "chart_type": "single_numeric",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Code Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_template_code(template_id: str, csv_path: str) -> str:
    """
    Generate Manim code for a specific template using sample data.

    Args:
        template_id: The template identifier
        csv_path: Path to the sample CSV data

    Returns:
        Generated Manim Python code string
    """
    from agents.tools.danim_templates import (
        generate_bar_race_code,
        generate_bubble_code,
        generate_line_evolution_code,
        generate_distribution_code,
        generate_bento_grid_code,
        generate_count_bar_code,
        generate_single_numeric_code,
    )

    config = TEMPLATE_CONFIGS.get(template_id)
    if not config:
        raise ValueError(f"Unknown template: {template_id}")

    spec = ChartSpec(
        chart_type=config["chart_type"],
        data_binding=config["binding"],
    )

    generators = {
        "generate_bar_race_code": generate_bar_race_code,
        "generate_bubble_code": generate_bubble_code,
        "generate_line_evolution_code": generate_line_evolution_code,
        "generate_distribution_code": generate_distribution_code,
        "generate_bento_grid_code": generate_bento_grid_code,
        "generate_count_bar_code": generate_count_bar_code,
        "generate_single_numeric_code": generate_single_numeric_code,
    }

    generator_name = config["generator"]
    generator_fn = generators.get(generator_name)

    if not generator_fn:
        raise ValueError(f"Unknown generator: {generator_name}")

    logger.info(f"Generating code for template: {template_id}")
    return generator_fn(spec, csv_path)


# ─────────────────────────────────────────────────────────────────────────────
# Video Rendering
# ─────────────────────────────────────────────────────────────────────────────

def render_to_video(code: str, output_dir: Path, template_id: str) -> Optional[Path]:
    """
    Render Manim code to a video file.

    Args:
        code: Manim Python code
        output_dir: Directory to save output
        template_id: Template identifier for naming

    Returns:
        Path to the rendered video file, or None if failed
    """
    work_dir = output_dir / f"work_{template_id}_{uuid.uuid4().hex[:8]}"
    work_dir.mkdir(parents=True, exist_ok=True)

    # Write code to file
    code_file = work_dir / "scene.py"
    with open(code_file, "w", encoding="utf-8") as f:
        f.write(code)

    logger.info(f"Rendering video for {template_id}...")

    # Quality flag mapping
    quality_flags = {
        "low": "-ql",
        "medium": "-qm",
        "high": "-qh",
    }

    quality_flag = quality_flags.get(MANIM_QUALITY, "-ql")

    try:
        result = subprocess.run(
            [
                "manim",
                quality_flag,
                "--fps", str(MANIM_FPS),
                str(code_file),
                "GenScene",
            ],
            capture_output=True,
            text=True,
            cwd=str(work_dir),
            timeout=120,  # 2 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"Manim render failed for {template_id}:")
            logger.error(result.stderr[:1000] if result.stderr else "No stderr")
            return None

        # Find the output video
        media_dir = work_dir / "media" / "videos" / "scene"

        # Look for video files
        video_patterns = ["*.mp4", "*.mov", "*.webm"]
        video_file = None

        for quality_dir in media_dir.glob("*"):
            if quality_dir.is_dir():
                for pattern in video_patterns:
                    videos = list(quality_dir.glob(pattern))
                    if videos:
                        video_file = videos[0]
                        break
            if video_file:
                break

        if not video_file or not video_file.exists():
            logger.error(f"No video output found for {template_id}")
            logger.debug(f"Searched in: {media_dir}")
            return None

        # Copy to output directory
        output_video = output_dir / f"{template_id}.mp4"
        shutil.copy(video_file, output_video)

        # Clean up work directory
        shutil.rmtree(work_dir, ignore_errors=True)

        logger.info(f"Video rendered: {output_video}")
        return output_video

    except subprocess.TimeoutExpired:
        logger.error(f"Render timeout for {template_id}")
        shutil.rmtree(work_dir, ignore_errors=True)
        return None
    except Exception as e:
        logger.error(f"Render error for {template_id}: {e}")
        shutil.rmtree(work_dir, ignore_errors=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# GIF Conversion
# ─────────────────────────────────────────────────────────────────────────────

def convert_to_gif(video_path: Path, output_path: Path) -> bool:
    """
    Convert a video file to an optimized GIF.

    Uses ffmpeg for conversion with palette generation for better quality.

    Args:
        video_path: Path to input video
        output_path: Path for output GIF

    Returns:
        True if successful, False otherwise
    """
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return False

    logger.info(f"Converting to GIF: {output_path.name}")

    # Get video duration
    try:
        probe_result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
        )
        duration = float(probe_result.stdout.strip())
    except Exception:
        duration = GIF_DURATION

    # Calculate speed factor to fit target duration
    speed_factor = max(1.0, duration / GIF_DURATION)

    # Generate palette for better GIF quality
    palette_path = video_path.parent / f"{video_path.stem}_palette.png"

    try:
        # Step 1: Generate palette
        filters = f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos"
        if speed_factor > 1.0:
            filters = f"setpts={1/speed_factor}*PTS," + filters

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-vf", f"{filters},palettegen=stats_mode=diff",
                str(palette_path),
            ],
            capture_output=True,
            check=True,
        )

        # Step 2: Create GIF using palette
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-i", str(palette_path),
                "-lavfi", f"{filters} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
                "-loop", "0",
                str(output_path),
            ],
            capture_output=True,
            check=True,
        )

        # Clean up palette
        palette_path.unlink(missing_ok=True)

        logger.info(f"GIF created: {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed: {e}")

        # Fallback: simple conversion without palette
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", str(video_path),
                    "-vf", f"fps={GIF_FPS},scale={GIF_WIDTH}:-1",
                    "-loop", "0",
                    str(output_path),
                ],
                capture_output=True,
                check=True,
            )
            logger.info(f"GIF created (fallback): {output_path}")
            return True
        except Exception as e2:
            logger.error(f"Fallback conversion also failed: {e2}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error during GIF conversion: {e}")
        return False
    finally:
        palette_path.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main Generation Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def generate_preview(template_id: str, sample_data_paths: Dict[str, str]) -> bool:
    """
    Generate a preview GIF for a single template.

    Args:
        template_id: The template to generate preview for
        sample_data_paths: Mapping of template_id to sample data CSV paths

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"=" * 60)
    logger.info(f"Generating preview for: {template_id}")
    logger.info(f"=" * 60)

    if template_id not in TEMPLATE_CONFIGS:
        logger.error(f"Unknown template: {template_id}")
        return False

    csv_path = sample_data_paths.get(template_id)
    if not csv_path or not Path(csv_path).exists():
        logger.error(f"Sample data not found for {template_id}")
        return False

    # Ensure output directory exists
    PREVIEWS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create temp directory for intermediate files
    temp_dir = Path(tempfile.mkdtemp(prefix=f"preview_{template_id}_"))

    try:
        # Step 1: Generate code
        code = generate_template_code(template_id, csv_path)

        # Step 2: Render to video
        video_path = render_to_video(code, temp_dir, template_id)
        if not video_path:
            logger.error(f"Failed to render video for {template_id}")
            return False

        # Step 3: Convert to GIF
        gif_path = PREVIEWS_OUTPUT_DIR / f"{template_id}.gif"
        if not convert_to_gif(video_path, gif_path):
            logger.error(f"Failed to convert to GIF for {template_id}")
            return False

        logger.info(f"✓ Preview generated: {gif_path}")
        return True

    except Exception as e:
        logger.error(f"Error generating preview for {template_id}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def generate_all_previews() -> Dict[str, bool]:
    """
    Generate preview GIFs for all templates.

    Returns:
        Dictionary mapping template_id to success status
    """
    logger.info("Creating sample datasets...")
    sample_data_paths = create_all_sample_data()

    results = {}
    for template_id in TEMPLATE_CONFIGS.keys():
        results[template_id] = generate_preview(template_id, sample_data_paths)

    return results


def print_summary(results: Dict[str, bool]) -> None:
    """Print a summary of generation results."""
    print("\n" + "=" * 60)
    print("PREVIEW GENERATION SUMMARY")
    print("=" * 60)

    successful = [t for t, s in results.items() if s]
    failed = [t for t, s in results.items() if not s]

    print(f"\n✓ Successful ({len(successful)}):")
    for t in successful:
        print(f"  - {t}")

    if failed:
        print(f"\n✗ Failed ({len(failed)}):")
        for t in failed:
            print(f"  - {t}")

    print(f"\nGIFs saved to: {PREVIEWS_OUTPUT_DIR}")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate preview GIFs for animation templates"
    )
    parser.add_argument(
        "--template", "-t",
        help="Generate preview for a specific template only",
        choices=list(TEMPLATE_CONFIGS.keys()),
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available templates",
    )
    parser.add_argument(
        "--quality", "-q",
        choices=["low", "medium", "high"],
        default="low",
        help="Manim render quality (default: low)",
    )
    parser.add_argument(
        "--width", "-w",
        type=int,
        default=480,
        help="GIF width in pixels (default: 480)",
    )

    args = parser.parse_args()

    if args.list:
        print("Available templates:")
        for template_id in TEMPLATE_CONFIGS.keys():
            print(f"  - {template_id}")
        return

    # Apply CLI settings
    global MANIM_QUALITY, GIF_WIDTH
    MANIM_QUALITY = args.quality
    GIF_WIDTH = args.width

    # Check dependencies
    if shutil.which("manim") is None:
        logger.error("Manim CLI not found. Please install: pip install manim")
        sys.exit(1)

    if shutil.which("ffmpeg") is None:
        logger.error("FFmpeg not found. Please install ffmpeg.")
        sys.exit(1)

    # Generate previews
    if args.template:
        sample_data_paths = create_all_sample_data()
        success = generate_preview(args.template, sample_data_paths)
        sys.exit(0 if success else 1)
    else:
        results = generate_all_previews()
        print_summary(results)

        # Exit with error if any failed
        if not all(results.values()):
            sys.exit(1)


if __name__ == "__main__":
    main()
