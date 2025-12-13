from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from api.routes.v1_router import v1_router
from api.settings import api_settings

logger = logging.getLogger(__name__)


def ensure_preview_placeholders() -> None:
    """
    Check if preview placeholder SVGs exist, and create them if not.

    This runs at startup to ensure the template gallery has preview images
    available even if GIF previews haven't been generated yet.
    """
    artifacts_dir = Path(os.getcwd()) / "artifacts"
    previews_dir = artifacts_dir / "previews"

    # List of expected placeholder files
    template_ids = [
        "bar_race",
        "bubble",
        "line_evolution",
        "distribution",
        "bento_grid",
        "count_bar",
        "single_numeric",
    ]

    # Check if any placeholders are missing
    missing = []
    for template_id in template_ids:
        placeholder_path = previews_dir / f"{template_id}_placeholder.svg"
        if not placeholder_path.exists():
            missing.append(template_id)

    if not missing:
        logger.info("All preview placeholders already exist")
        return

    logger.info(f"Missing preview placeholders: {missing}. Generating...")

    try:
        # Import and run the placeholder generator
        from scripts.previews.create_placeholders import create_placeholder_svgs
        created = create_placeholder_svgs()
        logger.info(f"Created {len(created)} preview placeholder SVGs")
    except Exception as e:
        logger.warning(f"Failed to generate preview placeholders: {e}")
        logger.warning("Template gallery will use fallback icons for previews")


def check_and_generate_gif_previews() -> None:
    """
    Check if GIF previews exist, and optionally generate them.

    This is a heavier operation that requires Manim, so it's controlled
    by an environment variable and runs in background.
    """
    if not os.environ.get("GENERATE_PREVIEW_GIFS", "").lower() in ("true", "1", "yes"):
        return

    artifacts_dir = Path(os.getcwd()) / "artifacts"
    previews_dir = artifacts_dir / "previews"

    template_ids = [
        "bar_race",
        "bubble",
        "line_evolution",
        "distribution",
        "bento_grid",
        "count_bar",
        "single_numeric",
    ]

    # Check which GIFs are missing
    missing = []
    for template_id in template_ids:
        gif_path = previews_dir / f"{template_id}.gif"
        if not gif_path.exists():
            missing.append(template_id)

    if not missing:
        logger.info("All GIF previews already exist")
        return

    logger.info(f"Missing GIF previews: {missing}")
    logger.info("GIF generation is enabled but will run in background thread")

    # Run GIF generation in background thread to not block startup
    import threading

    def generate_gifs():
        try:
            from scripts.previews.generate_previews import generate_all_previews
            results = generate_all_previews()
            successful = sum(1 for v in results.values() if v)
            logger.info(f"Generated {successful}/{len(results)} GIF previews")
        except Exception as e:
            logger.error(f"Failed to generate GIF previews: {e}")

    thread = threading.Thread(target=generate_gifs, daemon=True)
    thread.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting up Animation Engine API...")

    # Ensure artifacts directories exist
    artifacts_dir = os.path.join(os.getcwd(), "artifacts")
    previews_dir = os.path.join(artifacts_dir, "previews")
    os.makedirs(previews_dir, exist_ok=True)

    # Generate preview placeholders if missing
    ensure_preview_placeholders()

    # Optionally generate GIF previews (controlled by env var)
    check_and_generate_gif_previews()

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Animation Engine API...")


def create_app() -> FastAPI:
    """Create a FastAPI App"""

    # Create FastAPI App with lifespan
    app: FastAPI = FastAPI(
        title=api_settings.title,
        version=api_settings.version,
        docs_url="/docs" if api_settings.docs_enabled else None,
        redoc_url="/redoc" if api_settings.docs_enabled else None,
        openapi_url="/openapi.json" if api_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    # Add v1 router
    app.include_router(v1_router)

    # Add Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origin_list or [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # serve artifacts dir
    artifacts_dir = os.path.join(os.getcwd(), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=artifacts_dir), name="static")

    return app


# Create a FastAPI app
app = create_app()
