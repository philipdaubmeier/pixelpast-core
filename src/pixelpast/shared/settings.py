"""Application settings for PixelPast runtime services."""

from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    calendar_root: Path | None = Field(
        default=None,
        description="Root path for the calendar ingestion connector.",
    )
    spotify_root: Path | None = Field(
        default=None,
        description="Root path for the Spotify ingestion connector.",
    )
    lightroom_catalog_path: Path | None = Field(
        default=None,
        description="Catalog file path for the Lightroom catalog ingestion connector.",
    )
    google_maps_timeline_root: Path | None = Field(
        default=None,
        description="Root path for the Google Maps Timeline ingestion connector.",
    )
    workdays_vacation_root: Path | None = Field(
        default=None,
        description="Root path for the workdays-vacation ingestion connector.",
    )
    google_places_api_key: str | None = Field(
        default=None,
        description="API key for the Google Places derive job.",
    )
    google_places_language_code: str | None = Field(
        default=None,
        description="Optional language code for Google Places detail requests.",
    )
    google_places_region_code: str | None = Field(
        default=None,
        description="Optional region code for Google Places detail requests.",
    )
    google_places_refresh_max_age_days: int = Field(
        default=365 * 3,
        ge=1,
        description=(
            "Maximum cache age in days before the Google Places derive job "
            "refreshes a place snapshot."
        ),
    )
    day_context_max_days: int = Field(
        default=366,
        ge=1,
        description=(
            "Maximum inclusive day count allowed for "
            "/api/days/context requests."
        ),
    )

    @property
    def google_places_refresh_max_age(self) -> timedelta:
        """Return the Google Places cache staleness threshold as a timedelta."""

        return timedelta(days=self.google_places_refresh_max_age_days)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached process-wide settings for shared runtime services."""

    return Settings()
