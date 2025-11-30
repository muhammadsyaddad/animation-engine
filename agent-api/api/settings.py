from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    """Api settings that are set using environment variables."""

    title: str = "agent-api"
    version: str = "1.0"

    # Phase 4: Runtime and storage settings
    # Timeouts (seconds) for preview (PNG), final render (MP4), and export/merge (FFmpeg) pipelines
    preview_timeout_seconds: int = 600
    render_timeout_seconds: int = 1800
    export_timeout_seconds: int = 600

    # Preview sampling controls
    # Keep 1 of every N frames; cap the number returned to the UI
    preview_sample_every: int = 4
    preview_max_frames: int = 50

    # Default render options
    default_aspect_ratio: str = "16:9"  # Options: "16:9" | "9:16" | "1:1"
    default_render_quality: str = "medium"  # Options: "low"(-ql) | "medium"(-qm) | "high"(-qh)

    # Storage mode: when True, serve from local artifacts (/static); when False, upload to Azure Blob
    use_local_storage: bool = True
    azure_storage_connection_string: Optional[str] = None
    azure_storage_container_name: Optional[str] = None

    # Set to False to disable docs at /docs and /redoc
    docs_enabled: bool = True

    # Cors origin list to allow requests from.
    # This list is set using the set_cors_origin_list validator
    # which uses the runtime_env variable to set the
    # default cors origin list.
    cors_origin_list: Optional[List[str]] = Field(None, validate_default=True)

    @field_validator("cors_origin_list", mode="before")
    def set_cors_origin_list(cls, cors_origin_list, info: FieldValidationInfo):
        valid_cors = cors_origin_list or []

        # Add app.agno.com to cors to allow requests from the Agno playground.
        valid_cors.append("https://app.agno.com")
        # Add localhost to cors to allow requests from the local environment.
        valid_cors.append("http://localhost")
        # Add localhost:3000 to cors to allow requests from local Agent UI.
        valid_cors.append("http://localhost:3000")

        return valid_cors


# Create ApiSettings object
api_settings = ApiSettings()
