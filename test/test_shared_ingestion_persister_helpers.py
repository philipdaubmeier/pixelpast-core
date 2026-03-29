"""Tests for shared ingestion persister helpers."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from pixelpast.ingestion.persister_helpers import (
    compose_event_persistence_outcome,
    count_missing_events_for_source,
    persist_asset_candidate,
    require_source_external_id,
    upsert_required_source,
)
from pixelpast.persistence.repositories import EventReplaceResult


def test_persist_asset_candidate_shares_asset_linking_mechanics() -> None:
    asset_repository = _FakeAssetRepository()
    tag_repository = _FakeTagRepository()
    person_repository = _FakePersonRepository()

    outcome = persist_asset_candidate(
        source_id=7,
        asset_repository=asset_repository,
        tag_repository=tag_repository,
        person_repository=person_repository,
        asset=_FakeAssetCandidate(
            external_id="asset-1",
            media_type="photo",
            creator_name="Creator",
            tag_paths=("a", "a|b", "who|person"),
            asset_tag_paths=("a|b", "missing"),
            persons=(
                _FakePersonCandidate(name="Ada", path="who|Ada"),
                _FakePersonCandidate(name="Bob", path=None),
            ),
        ),
    )

    assert outcome == "updated"
    assert asset_repository.upsert_calls == [
        {
            "source_id": 7,
            "external_id": "asset-1",
            "media_type": "photo",
            "creator_person_id": 1,
        }
    ]
    assert tag_repository.paths == ["a", "a|b", "who|person"]
    assert asset_repository.replaced_tag_links == [(11, [3])]
    assert person_repository.calls == [
        ("Creator", None),
        ("Ada", "who|Ada"),
        ("Bob", None),
    ]
    assert asset_repository.replaced_person_links == [(11, [2, 3])]


def test_upsert_required_source_and_missing_preview_share_source_identity_logic() -> None:
    source_repository = _FakeSourceRepository()
    event_repository = _FakeEventRepository()

    source_id = upsert_required_source(
        source_repository=source_repository,
        source=_FakeSourceCandidate(
            type="calendar",
            name=None,
            external_id="source-123",
            config_json={"path": "/tmp"},
        ),
        default_name="Calendar",
        missing_external_id_message="missing external id",
    )
    missing_without_persisted_source = count_missing_events_for_source(
        source_repository=source_repository,
        event_repository=event_repository,
        source=_FakeSourceCandidate(
            type="calendar",
            name="Name wins",
            external_id="missing-source",
            config_json=None,
        ),
        event_payloads=[{"external_event_id": "event-1"}],
        missing_external_id_message="missing external id",
    )

    source_repository.sources_by_external_id["source-123"] = SimpleNamespace(id=41)
    missing_with_persisted_source = count_missing_events_for_source(
        source_repository=source_repository,
        event_repository=event_repository,
        source=_FakeSourceCandidate(
            type="calendar",
            name="Named Source",
            external_id="source-123",
            config_json=None,
        ),
        event_payloads=[{"external_event_id": "event-2"}],
        missing_external_id_message="missing external id",
    )

    assert source_id == 41
    assert source_repository.upsert_calls == [
        {
            "external_id": "source-123",
            "name": "source-123",
            "source_type": "calendar",
            "config": {"path": "/tmp"},
        }
    ]
    assert missing_without_persisted_source == 0
    assert missing_with_persisted_source == 5
    assert event_repository.count_missing_calls == [(41, [{"external_event_id": "event-2"}])]


def test_event_summary_and_external_id_validation_preserve_existing_wire_contract() -> None:
    with pytest.raises(ValueError, match="missing external id"):
        require_source_external_id(
            source_external_id=None,
            missing_external_id_message="missing external id",
        )

    summary = compose_event_persistence_outcome(
        event_result=EventReplaceResult(
            persisted_event_count=3,
            status="updated",
            inserted_event_count=1,
            updated_event_count=1,
            unchanged_event_count=1,
            missing_from_source_count=2,
        ),
        skipped_event_count=4,
        include_missing_from_source=True,
    )

    assert summary == (
        "inserted=1;updated=1;unchanged=1;missing_from_source=2;"
        "skipped=4;persisted_event_count=3"
    )


@dataclass(frozen=True, slots=True)
class _FakePersonCandidate:
    name: str
    path: str | None


@dataclass(frozen=True, slots=True)
class _FakeAssetCandidate:
    external_id: str
    media_type: str
    creator_name: str | None
    tag_paths: tuple[str, ...]
    asset_tag_paths: tuple[str, ...]
    persons: tuple[_FakePersonCandidate, ...]
    timestamp: object = "ts"
    summary: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    metadata_json: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class _FakeSourceCandidate:
    type: str
    name: str | None
    external_id: str | None
    config_json: dict[str, object] | None


class _FakeAssetRepository:
    def __init__(self) -> None:
        self.upsert_calls: list[dict[str, object]] = []
        self.replaced_tag_links: list[tuple[int, list[int]]] = []
        self.replaced_person_links: list[tuple[int, list[int]]] = []

    def upsert(self, **kwargs):
        self.upsert_calls.append(
            {
                "source_id": kwargs["source_id"],
                "external_id": kwargs["external_id"],
                "media_type": kwargs["media_type"],
                "creator_person_id": kwargs["creator_person_id"],
            }
        )
        return SimpleNamespace(asset=SimpleNamespace(id=11), status="unchanged")

    def replace_tag_links(self, *, asset_id: int, tag_ids):
        ids = list(tag_ids)
        self.replaced_tag_links.append((asset_id, ids))
        return True

    def replace_person_links(self, *, asset_id: int, person_ids):
        ids = list(person_ids)
        self.replaced_person_links.append((asset_id, ids))
        return False


class _FakeTagRepository:
    def __init__(self) -> None:
        self.paths: list[str] = []
        self._next_id = 1

    def get_or_create(self, *, path: str):
        self.paths.append(path)
        self._next_id += 1
        return SimpleNamespace(id=self._next_id)


class _FakePersonRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self._next_id = 0

    def get_or_create(self, *, name: str, path: str | None = None):
        self.calls.append((name, path))
        self._next_id += 1
        return SimpleNamespace(id=self._next_id)


class _FakeSourceRepository:
    def __init__(self) -> None:
        self.upsert_calls: list[dict[str, object]] = []
        self.sources_by_external_id: dict[str, object] = {}

    def upsert_by_external_id(self, **kwargs):
        self.upsert_calls.append(kwargs)
        source = SimpleNamespace(id=41)
        self.sources_by_external_id[kwargs["external_id"]] = source
        return SimpleNamespace(source=source, status="inserted")

    def get_by_external_id(self, *, external_id: str):
        return self.sources_by_external_id.get(external_id)


class _FakeEventRepository:
    def __init__(self) -> None:
        self.count_missing_calls: list[tuple[int, list[dict[str, object]]]] = []

    def count_missing_from_source(self, *, source_id: int, events):
        payloads = list(events)
        self.count_missing_calls.append((source_id, payloads))
        return 5
