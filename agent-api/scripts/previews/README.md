# Template Preview Generation

This directory contains scripts for generating preview images (GIFs) for animation templates.

## Overview

Each animation template in the system can have an associated preview that shows users what the animation looks like before they create one. These previews are:

1. **GIF Previews** - Short animated GIFs showing the actual animation output
2. **SVG Placeholders** - Static placeholder images used as fallbacks when GIFs aren't available

## Directory Structure

```
scripts/previews/
├── __init__.py              # Module exports
├── README.md                # This file
├── sample_data.py           # Creates sample datasets for each template
├── generate_previews.py     # Main script to render templates to GIFs
└── create_placeholders.py   # Creates SVG placeholder images
```

## Quick Start (Docker - Recommended)

### Automatic on Startup

**SVG placeholders are automatically generated when the API starts!**

When you run `docker-compose up`, the API checks for missing preview placeholders and creates them automatically. No manual action needed.

### Using the Admin API Endpoints

Once the API is running, you can manage previews via HTTP:

```bash
# Check preview status
curl http://localhost:8000/v1/admin/previews/status

# Regenerate SVG placeholders
curl -X POST http://localhost:8000/v1/admin/previews/regenerate \
  -H "Content-Type: application/json" \
  -d '{"regenerate_placeholders": true}'

# Generate GIF previews (runs in background)
curl -X POST http://localhost:8000/v1/admin/previews/regenerate \
  -H "Content-Type: application/json" \
  -d '{"regenerate_gifs": true, "async_gifs": true}'

# Regenerate specific templates only
curl -X POST http://localhost:8000/v1/admin/previews/regenerate \
  -H "Content-Type: application/json" \
  -d '{"regenerate_placeholders": true, "templates": ["bar_race", "bubble"]}'

# Delete GIF files (to force regeneration)
curl -X DELETE http://localhost:8000/v1/admin/previews/gifs
```

### Enable Automatic GIF Generation

To generate GIF previews automatically on startup, set the environment variable:

```yaml
# In docker-compose.yaml or .env
GENERATE_PREVIEW_GIFS: "true"
```

Or in your `.env` file:
```
GENERATE_PREVIEW_GIFS=true
```

GIFs are generated in a background thread so they don't block API startup.

### Run via Docker Exec

```bash
# Generate placeholders
docker-compose exec api python -m scripts.previews.create_placeholders

# Generate GIF previews
docker-compose exec api python -m scripts.previews.generate_previews

# Generate specific template
docker-compose exec api python -m scripts.previews.generate_previews --template bar_race

# List available templates
docker-compose exec api python -m scripts.previews.generate_previews --list
```

## Local Development (Without Docker)

### Create SVG Placeholders

```bash
cd agent-api
python -m scripts.previews.create_placeholders
```

### Generate GIF Previews

**Requirements:**
- Manim Community Edition (`pip install manim`)
- FFmpeg (for GIF conversion)

```bash
# Generate all previews
./scripts/generate_previews.sh

# Generate specific template
./scripts/generate_previews.sh bar_race

# List available templates
./scripts/generate_previews.sh --list

# Custom quality/size
./scripts/generate_previews.sh --quality medium --width 640
```

Or directly via Python:

```bash
cd agent-api

# Generate all
python -m scripts.previews.generate_previews

# Generate specific template
python -m scripts.previews.generate_previews --template bar_race

# List templates
python -m scripts.previews.generate_previews --list
```

## How It Works

### 1. Sample Data Creation (`sample_data.py`)

Creates realistic sample datasets for each template type:

| Template | Sample Data |
|----------|-------------|
| `bar_race` | Smartphone market share by brand over years |
| `bubble` | GDP vs Life Expectancy (Gapminder style) |
| `line_evolution` | Stock price over months |
| `distribution` | Test score distribution over years |
| `bento_grid` | Company KPI metrics |
| `count_bar` | Product category counts |
| `single_numeric` | Sales by region |

### 2. Preview Generation (`generate_previews.py`)

For each template:
1. Creates sample data using `sample_data.py`
2. Generates Manim code using the template generator from `agents/tools/danim_templates.py`
3. Renders the code to video using Manim CLI
4. Converts video to optimized GIF using FFmpeg with palette generation

### 3. Placeholder Creation (`create_placeholders.py`)

Creates SVG images that visually represent each template type:
- Uses consistent dark theme matching the app
- Shows stylized representation of the animation output
- Includes a play button indicator
- Small file size (~2-4KB each)

## Output Files

All preview files are saved to `artifacts/previews/`:

```
artifacts/previews/
├── bar_race.gif                    # Animated GIF (when generated)
├── bar_race_placeholder.svg        # SVG fallback
├── bubble.gif
├── bubble_placeholder.svg
├── line_evolution.gif
├── line_evolution_placeholder.svg
├── distribution.gif
├── distribution_placeholder.svg
├── bento_grid.gif
├── bento_grid_placeholder.svg
├── count_bar.gif
├── count_bar_placeholder.svg
├── single_numeric.gif
└── single_numeric_placeholder.svg
```

## API Integration

The template API endpoints automatically detect which preview files exist:

- `preview_url`: Path to GIF (e.g., `/static/previews/bar_race.gif`)
- `preview_fallback_url`: Path to SVG placeholder (e.g., `/static/previews/bar_race_placeholder.svg`)

The frontend `TemplateCard` component handles loading:
1. Attempts to load the GIF
2. Shows loading spinner while loading
3. Falls back to SVG placeholder if GIF fails or doesn't exist
4. Shows generic icon placeholder if neither exists

## Configuration

### GIF Settings (in `generate_previews.py`)

```python
GIF_WIDTH = 480       # Width in pixels
GIF_FPS = 12          # Frames per second
GIF_DURATION = 5      # Target duration in seconds
MANIM_QUALITY = "low" # Render quality: low, medium, high
```

### CLI Options

```
--template, -t    Generate preview for specific template only
--quality, -q     Manim render quality (low/medium/high)
--width, -w       GIF width in pixels
--list, -l        List available templates
```

## Admin API Reference

### GET /v1/admin/previews/status

Returns status of all preview files.

**Response:**
```json
{
  "previews_dir": "/app/artifacts/previews",
  "templates": [
    {
      "template_id": "bar_race",
      "gif_exists": true,
      "gif_path": "/app/artifacts/previews/bar_race.gif",
      "placeholder_exists": true,
      "placeholder_path": "/app/artifacts/previews/bar_race_placeholder.svg"
    }
  ],
  "total_gifs": 7,
  "total_placeholders": 7,
  "all_placeholders_exist": true,
  "all_gifs_exist": true
}
```

### POST /v1/admin/previews/regenerate

Trigger regeneration of preview files.

**Request Body:**
```json
{
  "regenerate_placeholders": true,
  "regenerate_gifs": false,
  "templates": null,
  "async_gifs": true
}
```

**Parameters:**
- `regenerate_placeholders` (bool): Generate SVG placeholders (fast)
- `regenerate_gifs` (bool): Generate animated GIFs (slow)
- `templates` (list|null): Specific template IDs, or null for all
- `async_gifs` (bool): Run GIF generation in background

### DELETE /v1/admin/previews/gifs

Delete GIF preview files (useful for forcing regeneration).

**Query Parameters:**
- `templates` (list): Specific templates to delete, or omit for all

## Adding New Templates

When adding a new template:

1. Add template configuration to `TEMPLATE_CONFIGS` in `generate_previews.py`
2. Create sample data function in `sample_data.py`
3. Add SVG placeholder to `SVG_TEMPLATES` in `create_placeholders.py`
4. Add template ID to `TEMPLATE_IDS` list in `api/routes/admin.py`
5. Restart the API (placeholders auto-generate) or call the regenerate endpoint

## Troubleshooting

### "Manim CLI not found"
Install Manim: `pip install manim`

### "FFmpeg not found"
Install FFmpeg:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`
- Windows: Download from https://ffmpeg.org/

### Preview generation fails
Check the logs for the specific template. Common issues:
- Missing data columns in sample data
- Template generator raising exceptions
- Manim rendering timeout (try reducing animation complexity)

### GIF too large
Reduce `GIF_WIDTH` or `GIF_FPS`, or increase compression in FFmpeg settings.

### Previews not showing in UI
1. Check the API logs for startup messages about placeholder generation
2. Verify files exist: `docker-compose exec api ls -la artifacts/previews/`
3. Check the status endpoint: `curl http://localhost:8000/v1/admin/previews/status`
4. Ensure the `/static` route is working: `curl http://localhost:8000/static/previews/bar_race_placeholder.svg`

### Docker volume issues
If previews disappear after restart, ensure `artifacts/` is properly mounted:
```yaml
volumes:
  - .:/app  # This mounts the entire project including artifacts/
```