#!/bin/bash
# Generate preview GIFs for all animation templates
#
# Usage:
#   ./scripts/generate_previews.sh            # Generate all previews
#   ./scripts/generate_previews.sh bar_race   # Generate specific template
#   ./scripts/generate_previews.sh --list     # List available templates
#
# Requirements:
#   - Python 3.9+
#   - Manim Community Edition
#   - FFmpeg

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check for required dependencies
check_dependencies() {
    local missing=()

    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi

    if ! command -v manim &> /dev/null; then
        missing+=("manim (pip install manim)")
    fi

    if ! command -v ffmpeg &> /dev/null; then
        missing+=("ffmpeg")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        echo "Error: Missing required dependencies:"
        for dep in "${missing[@]}"; do
            echo "  - $dep"
        done
        exit 1
    fi
}

# Show help
show_help() {
    echo "Generate preview GIFs for animation templates"
    echo ""
    echo "Usage:"
    echo "  $0                      Generate all previews"
    echo "  $0 <template_id>        Generate preview for specific template"
    echo "  $0 --list               List available templates"
    echo "  $0 --help               Show this help message"
    echo ""
    echo "Options:"
    echo "  --quality, -q <low|medium|high>  Manim render quality (default: low)"
    echo "  --width, -w <pixels>             GIF width in pixels (default: 480)"
    echo ""
    echo "Examples:"
    echo "  $0 bar_race             Generate preview for bar_race template"
    echo "  $0 -q medium            Generate all previews in medium quality"
}

# Parse arguments
TEMPLATE=""
QUALITY="low"
WIDTH="480"

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --list|-l)
            check_dependencies
            python3 -m scripts.previews.generate_previews --list
            exit 0
            ;;
        --quality|-q)
            QUALITY="$2"
            shift 2
            ;;
        --width|-w)
            WIDTH="$2"
            shift 2
            ;;
        *)
            TEMPLATE="$1"
            shift
            ;;
    esac
done

check_dependencies

echo "================================================"
echo "  Animation Template Preview Generator"
echo "================================================"
echo ""

if [ -n "$TEMPLATE" ]; then
    echo "Generating preview for: $TEMPLATE"
    echo "Quality: $QUALITY | Width: ${WIDTH}px"
    echo ""
    python3 -m scripts.previews.generate_previews --template "$TEMPLATE" --quality "$QUALITY" --width "$WIDTH"
else
    echo "Generating previews for all templates"
    echo "Quality: $QUALITY | Width: ${WIDTH}px"
    echo ""
    python3 -m scripts.previews.generate_previews --quality "$QUALITY" --width "$WIDTH"
fi

echo ""
echo "Done! Previews saved to: artifacts/previews/"
