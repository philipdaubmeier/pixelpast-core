"""Minimal canonical repositories for ingestion workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import Asset, ImportRun, Source


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class SourceRepository:
    """Repository for canonical source records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_type_and_name(self, *, source_type: str, name: str) -> Source | None:
        """Return the configured source matching a connector type and name."""

        statement = (
            select(Source)
            .where(Source.type == source_type, Source.name == name)
            .order_by(Source.id)
        )
        return self._session.execute(statement).scalars().first()

    def get_or_create(
        self,
        *,
        name: str,
        source_type: str,
        config: dict[str, Any],
    ) -> Source:
        """Return an existing source or create one for the connector."""

        source = self.get_by_type_and_name(source_type=source_type, name=name)
        if source is None:
            source = Source(name=name, type=source_type, config=dict(config))
            self._session.add(source)
            self._session.flush()
            return source

        source.name = name
        source.config = dict(config)
        self._session.flush()
        return source


class ImportRunRepository:
    """Repository for ingestion run tracking."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        source_id: int,
        mode: str,
        status: str = "running",
        started_at: datetime | None = None,
    ) -> ImportRun:
        """Create and persist a running import record."""

        import_run = ImportRun(
            source_id=source_id,
            started_at=started_at or utc_now(),
            finished_at=None,
            status=status,
            mode=mode,
        )
        self._session.add(import_run)
        self._session.flush()
        return import_run

    def get_by_id(self, *, import_run_id: int) -> ImportRun | None:
        """Return an import run by identifier."""

        statement = select(ImportRun).where(ImportRun.id == import_run_id)
        return self._session.execute(statement).scalar_one_or_none()

    def mark_finished(
        self,
        import_run: ImportRun,
        *,
        status: str,
        finished_at: datetime | None = None,
    ) -> ImportRun:
        """Mark an import run as finished with a terminal status."""

        import_run.status = status
        import_run.finished_at = finished_at or utc_now()
        self._session.flush()
        return import_run

    def mark_finished_by_id(
        self,
        *,
        import_run_id: int,
        status: str,
        finished_at: datetime | None = None,
    ) -> ImportRun | None:
        """Mark an import run as finished when only the identifier is available."""

        import_run = self.get_by_id(import_run_id=import_run_id)
        if import_run is None:
            return None
        return self.mark_finished(
            import_run,
            status=status,
            finished_at=finished_at,
        )


class AssetRepository:
    """Repository for canonical asset upserts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_external_id(self, *, external_id: str) -> Asset | None:
        """Return an asset identified by its stable source-specific key."""

        statement = select(Asset).where(Asset.external_id == external_id)
        return self._session.execute(statement).scalar_one_or_none()

    def upsert(
        self,
        *,
        external_id: str,
        media_type: str,
        timestamp: datetime,
        latitude: float | None,
        longitude: float | None,
        metadata_json: dict[str, Any] | None,
    ) -> Asset:
        """Insert or update an asset by external identifier."""

        asset = self.get_by_external_id(external_id=external_id)
        if asset is None:
            asset = Asset(
                external_id=external_id,
                media_type=media_type,
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                metadata_json=(
                    dict(metadata_json) if metadata_json is not None else None
                ),
            )
            self._session.add(asset)
            self._session.flush()
            return asset

        asset.media_type = media_type
        asset.timestamp = timestamp
        asset.latitude = latitude
        asset.longitude = longitude
        asset.metadata_json = (
            dict(metadata_json) if metadata_json is not None else None
        )
        self._session.flush()
        return asset
