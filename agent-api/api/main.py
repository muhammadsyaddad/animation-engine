from contextlib import asynccontextmanager
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from api.routes.v1_router import v1_router
from api.settings import api_settings


def configure_logging():
    """
    Configure comprehensive logging for the animation pipeline.

    This sets up logging for all pipeline modules with a consistent format
    that includes timestamps, log levels, and module names for easy debugging.
    """
    # Get log level from environment or default to INFO
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create a formatter with detailed information
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(console_handler)

    # Configure specific loggers for the animation pipeline
    pipeline_loggers = [
        "animation_pipeline",
        "animation_pipeline.preview_manim",
        "animation_pipeline.video_manim",
        "animation_pipeline.templates",
        "animation_pipeline.templates.line_evolution",
        "animation_pipeline.templates.distribution",
        "animation_pipeline.templates.count_bar",
        "animation_pipeline.templates.single_numeric",
        "animation_pipeline.templates.bar_race",
        "animation_pipeline.templates.bubble_chart",
        "api.routes.agents",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ]

    for logger_name in pipeline_loggers:
        module_logger = logging.getLogger(logger_name)
        module_logger.setLevel(log_level)
        # Don't propagate to root to avoid duplicate logs
        module_logger.propagate = True

    # Log the configuration
    logging.info(f"Logging configured | level={log_level_str} | handlers=console")
    logging.info("Pipeline loggers configured for comprehensive tracing")


# Configure logging early
configure_logging()

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
    logger.info("=" * 60)
    logger.info("ANIMATION ENGINE API STARTING UP")
    logger.info("=" * 60)
    logger.info(f"Environment | LOG_LEVEL={os.environ.get('LOG_LEVEL', 'INFO')}")
    logger.info(f"Environment | AUTO_SELECT_TEMPLATES={api_settings.auto_select_templates}")

    # Ensure artifacts directories exist
    artifacts_dir = os.path.join(os.getcwd(), "artifacts")
    previews_dir = os.path.join(artifacts_dir, "previews")
    os.makedirs(previews_dir, exist_ok=True)

    # Generate preview placeholders if missing
    ensure_preview_placeholders()

    # Optionally generate GIF previews (controlled by env var)
    check_and_generate_gif_previews()

    logger.info("=" * 60)
    logger.info("API STARTUP COMPLETE - READY TO ACCEPT REQUESTS")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("ANIMATION ENGINE API SHUTTING DOWN")
    logger.info("=" * 60)


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
