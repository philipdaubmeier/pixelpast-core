"""Application settings for PixelPast runtime services."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "var" / "pixelpast.db"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="PIXELPAST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PixelPast"
    app_env: str = "development"
    debug: bool = False
    database_url: str = Field(
        default=f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}",
        description="SQLAlchemy database URL.",
    )
    timeline_projection_provider: Literal["database", "demo"] = Field(
        default="database",
        description=(
            "Projection provider for exploration-oriented API endpoints."
        ),
    )
    photos_root: Path | None = Field(
        default=None,
        description="Root directory for the photo ingestion connector.",
    )
    day_context_max_days: int = Field(
        default=366,
        ge=1,
        description="Maximum inclusive day count allowed for /days/context requests.",
    )
    api_cors_allowed_origins: tuple[str, ...] = Field(
        default=("http://localhost:5173", "http://127.0.0.1:5173"),
        description="Allowed CORS origins for local UI development.",
    )

    @field_validator("api_cors_allowed_origins", mode="before")
    @classmethod
    def _normalize_api_cors_allowed_origins(
        cls,
        value: str | list[str] | tuple[str, ...],
    ) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(
                origin.strip() for origin in value.split(",") if origin.strip()
            )
        return tuple(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached process-wide settings for shared runtime services."""

    return Settings()
