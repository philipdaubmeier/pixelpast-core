"""Application settings for PixelPast runtime services."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
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
    photos_root: Path | None = Field(
        default=None,
        description="Root directory for the photo ingestion connector.",
    )
    day_context_max_days: int = Field(
        default=366,
        ge=1,
        description="Maximum inclusive day count allowed for /days/context requests.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached process-wide settings for shared runtime services."""

    return Settings()
