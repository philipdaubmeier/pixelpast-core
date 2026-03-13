"""Minimal canonical repositories for ingestion workflows."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pixelpast.persistence.models import (
    Asset,
    AssetPerson,
    AssetTag,
    ImportRun,
    Person,
    Source,
    Tag,
)


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
        summary: str | None,
        latitude: float | None,
        longitude: float | None,
        creator_person_id: int | None,
        metadata_json: dict[str, Any] | None,
    ) -> Asset:
        """Insert or update an asset by external identifier."""

        asset = self.get_by_external_id(external_id=external_id)
        if asset is None:
            asset = Asset(
                external_id=external_id,
                media_type=media_type,
                timestamp=timestamp,
                summary=summary,
                latitude=latitude,
                longitude=longitude,
                creator_person_id=creator_person_id,
                metadata_json=(
                    dict(metadata_json) if metadata_json is not None else None
                ),
            )
            self._session.add(asset)
            self._session.flush()
            return asset

        asset.media_type = media_type
        asset.timestamp = timestamp
        asset.summary = summary
        asset.latitude = latitude
        asset.longitude = longitude
        asset.creator_person_id = creator_person_id
        asset.metadata_json = (
            dict(metadata_json) if metadata_json is not None else None
        )
        self._session.flush()
        return asset

    def replace_tag_links(self, *, asset_id: int, tag_ids: Iterable[int]) -> None:
        """Replace all asset-tag links with the provided deterministic set."""

        self._session.execute(delete(AssetTag).where(AssetTag.asset_id == asset_id))
        unique_tag_ids = sorted(set(tag_ids))
        self._session.add_all(
            [AssetTag(asset_id=asset_id, tag_id=tag_id) for tag_id in unique_tag_ids]
        )
        self._session.flush()

    def replace_person_links(
        self,
        *,
        asset_id: int,
        person_ids: Iterable[int],
    ) -> None:
        """Replace all asset-person links with the provided deterministic set."""

        self._session.execute(
            delete(AssetPerson).where(AssetPerson.asset_id == asset_id)
        )
        unique_person_ids = sorted(set(person_ids))
        self._session.add_all(
            [
                AssetPerson(asset_id=asset_id, person_id=person_id)
                for person_id in unique_person_ids
            ]
        )
        self._session.flush()


class TagRepository:
    """Repository for canonical tag creation and lookup."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_path(self, *, path: str) -> Tag | None:
        """Return a tag by its normalized canonical path."""

        statement = select(Tag).where(Tag.path == path)
        return self._session.execute(statement).scalar_one_or_none()

    def get_or_create(
        self,
        *,
        path: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> Tag:
        """Return an existing tag or create one from a canonical path."""

        tag = self.get_by_path(path=path)
        label = path.rsplit("|", 1)[-1]
        if tag is None:
            tag = Tag(
                label=label,
                path=path,
                metadata_json=(
                    dict(metadata_json) if metadata_json is not None else None
                ),
            )
            self._session.add(tag)
            self._session.flush()
            return tag

        tag.label = label
        if metadata_json is not None:
            tag.metadata_json = dict(metadata_json)
        self._session.flush()
        return tag


class PersonRepository:
    """Repository for canonical person creation and lookup."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_path(self, *, path: str) -> Person | None:
        """Return a person by canonical path when available."""

        statement = select(Person).where(Person.path == path)
        return self._session.execute(statement).scalar_one_or_none()

    def get_by_name(self, *, name: str) -> Person | None:
        """Return the first person matching a canonical display name."""

        statement = select(Person).where(Person.name == name).order_by(Person.id)
        return self._session.execute(statement).scalars().first()

    def get_or_create(
        self,
        *,
        name: str,
        path: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> Person:
        """Return a canonical person, preferring path-based identity when present."""

        person = None
        if path is not None:
            person = self.get_by_path(path=path)
        if person is None:
            person = self.get_by_name(name=name)

        if person is None:
            person = Person(
                name=name,
                path=path,
                metadata_json=(
                    dict(metadata_json) if metadata_json is not None else None
                ),
            )
            self._session.add(person)
            self._session.flush()
            return person

        person.name = name
        if person.path is None and path is not None:
            person.path = path
        if metadata_json is not None:
            person.metadata_json = dict(metadata_json)
        self._session.flush()
        return person
