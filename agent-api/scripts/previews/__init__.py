"""
Preview generation scripts for animation templates.

This module provides utilities for generating preview GIFs
for each animation template type.

Usage:
    python -m scripts.previews.generate_previews [--template TEMPLATE_ID]
"""

from scripts.previews.sample_data import create_all_sample_data
from scripts.previews.generate_previews import (
    generate_preview,
    generate_all_previews,
    TEMPLATE_CONFIGS,
)

__all__ = [
    "create_all_sample_data",
    "generate_preview",
    "generate_all_previews",
    "TEMPLATE_CONFIGS",
]
