"""Spotify streaming-history parsing and canonical transformation helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

from pixelpast.ingestion.spotify.contracts import (
    LoadedSpotifyStreamingHistoryDocument,
    ParsedSpotifyStreamingHistoryDocument,
    ParsedSpotifyStreamRow,
    SpotifyAccountSourceCandidate,
    SpotifyEventCandidate,
    SpotifyStreamingHistoryDocumentDescriptor,
)

_RAW_PAYLOAD_FIELDS = (
    "username",
    "platform",
    "conn_country",
    "spotify_track_uri",
    "spotify_episode_uri",
    "shuffle",
    "skipped",
)


def parse_spotify_streaming_history_document(
    *,
    descriptor: SpotifyStreamingHistoryDocumentDescriptor,
    text: str,
) -> ParsedSpotifyStreamingHistoryDocument:
    """Parse one Spotify streaming-history JSON array into explicit row contracts."""

    return parse_loaded_spotify_streaming_history_document(
        LoadedSpotifyStreamingHistoryDocument(descriptor=descriptor, text=text)
    )


def parse_loaded_spotify_streaming_history_document(
    document: LoadedSpotifyStreamingHistoryDocument,
) -> ParsedSpotifyStreamingHistoryDocument:
    """Parse one loaded Spotify document payload into normalized row contracts."""

    try:
        payload = json.loads(document.text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Spotify streaming-history document is not valid JSON: "
            f"{document.descriptor.origin_label}"
        ) from error

    if not isinstance(payload, list):
        raise ValueError(
            "Spotify streaming-history document must contain a top-level JSON array: "
            f"{document.descriptor.origin_label}"
        )

    rows: list[ParsedSpotifyStreamRow] = []
    for row_index, raw_row in enumerate(payload):
        if not isinstance(raw_row, dict):
            raise ValueError(
                "Spotify streaming-history row must be a JSON object at index "
                f"{row_index}: {document.descriptor.origin_label}"
            )
        rows.append(_parse_stream_row(raw_row))

    return ParsedSpotifyStreamingHistoryDocument(
        descriptor=document.descriptor,
        rows=tuple(rows),
    )


def build_spotify_account_source_candidates(
    documents: Iterable[ParsedSpotifyStreamingHistoryDocument],
) -> tuple[SpotifyAccountSourceCandidate, ...]:
    """Build one canonical source candidate per normalized Spotify username."""

    candidates_by_external_id: dict[str, SpotifyAccountSourceCandidate] = {}
    origin_labels_by_username: dict[str, set[str]] = {}

    for document in documents:
        for row in document.rows:
            if row.normalized_username is None:
                continue
            external_id = _build_source_external_id(row.normalized_username)
            origin_labels = origin_labels_by_username.setdefault(
                row.normalized_username,
                set(),
            )
            origin_labels.add(document.descriptor.origin_label)
            if external_id in candidates_by_external_id:
                continue
            candidates_by_external_id[external_id] = SpotifyAccountSourceCandidate(
                type="spotify",
                name=row.normalized_username,
                external_id=external_id,
                config_json=None,
            )

    resolved_candidates: list[SpotifyAccountSourceCandidate] = []
    for external_id in sorted(candidates_by_external_id):
        candidate = candidates_by_external_id[external_id]
        normalized_username = candidate.name
        resolved_candidates.append(
            SpotifyAccountSourceCandidate(
                type=candidate.type,
                name=candidate.name,
                external_id=candidate.external_id,
                config_json={
                    "username": normalized_username,
                    "origin_labels": sorted(
                        origin_labels_by_username.get(normalized_username or "", set())
                    ),
                },
            )
        )
    return tuple(resolved_candidates)


def build_spotify_event_candidates(
    document: ParsedSpotifyStreamingHistoryDocument,
) -> tuple[SpotifyEventCandidate, ...]:
    """Build canonical Spotify event candidates for one parsed document."""

    return tuple(_build_event_candidate(row) for row in document.rows)


def _parse_stream_row(raw_row: dict[str, Any]) -> ParsedSpotifyStreamRow:
    timestamp_end = _parse_utc_timestamp(raw_row.get("ts"))
    ms_played = _parse_ms_played(raw_row.get("ms_played"))
    username = _trimmed_string(raw_row.get("username"))

    return ParsedSpotifyStreamRow(
        username=username,
        normalized_username=_normalize_username(username),
        timestamp_end=timestamp_end,
        ms_played=ms_played,
        platform=_trimmed_string(raw_row.get("platform")),
        conn_country=_trimmed_string(raw_row.get("conn_country")),
        master_metadata_track_name=_trimmed_string(
            raw_row.get("master_metadata_track_name")
        ),
        master_metadata_album_artist_name=_trimmed_string(
            raw_row.get("master_metadata_album_artist_name")
        ),
        spotify_track_uri=_trimmed_string(raw_row.get("spotify_track_uri")),
        episode_name=_trimmed_string(raw_row.get("episode_name")),
        episode_show_name=_trimmed_string(raw_row.get("episode_show_name")),
        spotify_episode_uri=_trimmed_string(raw_row.get("spotify_episode_uri")),
        shuffle=_parse_optional_bool(raw_row.get("shuffle"), field_name="shuffle"),
        skipped=_parse_optional_bool(raw_row.get("skipped"), field_name="skipped"),
        raw_payload={field: raw_row.get(field) for field in _RAW_PAYLOAD_FIELDS},
    )


def _build_event_candidate(row: ParsedSpotifyStreamRow) -> SpotifyEventCandidate:
    timestamp_start = row.timestamp_end - timedelta(milliseconds=row.ms_played)
    return SpotifyEventCandidate(
        source_external_id=(
            _build_source_external_id(row.normalized_username)
            if row.normalized_username is not None
            else None
        ),
        external_event_id=None,
        type="music_play",
        timestamp_start=timestamp_start,
        timestamp_end=row.timestamp_end,
        title=_build_title(row),
        summary=None,
        raw_payload=dict(row.raw_payload),
        derived_payload=None,
    )


def _build_title(row: ParsedSpotifyStreamRow) -> str:
    artist = row.master_metadata_album_artist_name
    title = row.master_metadata_track_name
    if artist is None or title is None:
        return ""
    return f"{artist} - {title}"


def _parse_utc_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Spotify streaming-history row is missing a valid 'ts' value.")

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    elif " " in normalized and "T" not in normalized:
        normalized = normalized.replace(" ", "T") + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(
            "Spotify streaming-history row contains an invalid UTC timestamp: "
            f"{value!r}"
        ) from error

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_ms_played(value: object) -> int:
    if not isinstance(value, int):
        raise ValueError(
            "Spotify streaming-history row is missing a valid integer 'ms_played' value."
        )
    if value < 0:
        raise ValueError(
            "Spotify streaming-history row contains a negative 'ms_played' value."
        )
    return value


def _parse_optional_bool(value: object, *, field_name: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ValueError(
        f"Spotify streaming-history row contains an invalid '{field_name}' value."
    )


def _trimmed_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_username(username: str | None) -> str | None:
    if username is None:
        return None
    normalized = username.strip().casefold()
    return normalized or None


def _build_source_external_id(normalized_username: str) -> str:
    return f"spotify:{normalized_username}"


__all__ = [
    "build_spotify_account_source_candidates",
    "build_spotify_event_candidates",
    "parse_loaded_spotify_streaming_history_document",
    "parse_spotify_streaming_history_document",
]
