from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from api.routes.v1_router import v1_router
from api.settings import api_settings
import os


def create_app() -> FastAPI:
    """Create a FastAPI App"""

    # Create FastAPI App
    app: FastAPI = FastAPI(
        title=api_settings.title,
        version=api_settings.version,
        docs_url="/docs" if api_settings.docs_enabled else None,
        redoc_url="/redoc" if api_settings.docs_enabled else None,
        openapi_url="/openapi.json" if api_settings.docs_enabled else None,
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
