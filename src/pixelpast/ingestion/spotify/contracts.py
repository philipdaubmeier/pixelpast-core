"""Public data contracts for Spotify streaming-history ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class SpotifyStreamingHistoryDocumentDescriptor:
    """One discovered Spotify streaming-history document."""

    path: Path
    archive_member_path: str | None = None

    @property
    def origin_path(self) -> Path:
        """Return the normalized filesystem path for this document."""

        return self.path.expanduser().resolve()

    @property
    def origin_label(self) -> str:
        """Return the deterministic human-readable document identifier."""

        origin_path = self.origin_path.as_posix()
        if self.archive_member_path is None:
            return origin_path
        return f"{origin_path}::{self.archive_member_path}"

    @property
    def is_archive_member(self) -> bool:
        """Return whether the document originates from a zip member."""

        return self.archive_member_path is not None


@dataclass(slots=True, frozen=True)
class LoadedSpotifyStreamingHistoryDocument:
    """Raw loaded text payload for one streaming-history document."""

    descriptor: SpotifyStreamingHistoryDocumentDescriptor
    text: str


@dataclass(slots=True, frozen=True)
class SpotifyStreamingHistoryDiscoveryResult:
    """Deterministic discovery result for one Spotify intake root."""

    documents: tuple[SpotifyStreamingHistoryDocumentDescriptor, ...]
    skipped_json_file_count: int = 0


@dataclass(slots=True, frozen=True)
class ParsedSpotifyStreamRow:
    """One parsed Spotify streaming-history row prior to canonical mapping."""

    row_index: int
    document_origin_label: str
    username: str | None
    normalized_username: str
    timestamp_end: datetime
    ms_played: int
    platform: str | None
    conn_country: str | None
    master_metadata_track_name: str | None
    master_metadata_album_artist_name: str | None
    spotify_track_uri: str | None
    episode_name: str | None
    episode_show_name: str | None
    spotify_episode_uri: str | None
    shuffle: bool | None
    skipped: bool | None
    raw_payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ParsedSpotifyStreamingHistoryDocument:
    """Parsed Spotify document payload and its normalized rows."""

    descriptor: SpotifyStreamingHistoryDocumentDescriptor
    rows: tuple[ParsedSpotifyStreamRow, ...]
    warning_messages: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class SpotifyAccountDocumentGroup:
    """All parsed rows that belong to one normalized Spotify username."""

    normalized_username: str
    source_external_id: str
    documents: tuple[ParsedSpotifyStreamingHistoryDocument, ...]
    rows: tuple[ParsedSpotifyStreamRow, ...]


@dataclass(slots=True, frozen=True)
class SpotifyAccountSourceCandidate:
    """Canonical source candidate representing one Spotify account."""

    type: str
    name: str
    external_id: str
    config_json: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class SpotifyAccountCandidate:
    """One persistable Spotify account replacement set."""

    normalized_username: str
    documents: tuple[SpotifyStreamingHistoryDocumentDescriptor, ...]
    source: SpotifyAccountSourceCandidate
    events: tuple["SpotifyEventCandidate", ...]


@dataclass(slots=True, frozen=True)
class SpotifyEventCandidate:
    """Canonical event candidate derived from one Spotify stream row."""

    source_external_id: str
    external_event_id: str | None
    type: str
    timestamp_start: datetime
    timestamp_end: datetime | None
    title: str | None
    summary: str | None
    raw_payload: dict[str, Any] | None
    derived_payload: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class SpotifyDocumentCandidate:
    """One transformed Spotify document with account and event candidates."""

    document: SpotifyStreamingHistoryDocumentDescriptor
    rows: tuple[ParsedSpotifyStreamRow, ...]
    source_candidates: tuple[SpotifyAccountSourceCandidate, ...]
    events: tuple[SpotifyEventCandidate, ...]


@dataclass(slots=True, frozen=True)
class SpotifyTransformError:
    """Represents one non-fatal Spotify document transform failure."""

    document: SpotifyStreamingHistoryDocumentDescriptor
    message: str


@dataclass(slots=True, frozen=True)
class SpotifyIngestionResult:
    """Summary of a completed Spotify ingestion run."""

    run_id: int
    processed_document_count: int
    persisted_source_count: int
    persisted_event_count: int
    error_count: int
    status: str
    skipped_json_file_count: int = 0
    warning_messages: tuple[str, ...] = ()
    transform_errors: tuple[SpotifyTransformError, ...] = ()


__all__ = [
    "LoadedSpotifyStreamingHistoryDocument",
    "SpotifyAccountCandidate",
    "SpotifyAccountDocumentGroup",
    "SpotifyStreamingHistoryDiscoveryResult",
    "ParsedSpotifyStreamingHistoryDocument",
    "ParsedSpotifyStreamRow",
    "SpotifyAccountSourceCandidate",
    "SpotifyDocumentCandidate",
    "SpotifyEventCandidate",
    "SpotifyIngestionResult",
    "SpotifyStreamingHistoryDocumentDescriptor",
    "SpotifyTransformError",
]
