"""Spotify ingestion contracts and transform helpers."""

from pixelpast.ingestion.spotify.contracts import (
    LoadedSpotifyStreamingHistoryDocument,
    ParsedSpotifyStreamingHistoryDocument,
    ParsedSpotifyStreamRow,
    SpotifyAccountSourceCandidate,
    SpotifyDocumentCandidate,
    SpotifyEventCandidate,
    SpotifyIngestionResult,
    SpotifyStreamingHistoryDocumentDescriptor,
    SpotifyTransformError,
)
from pixelpast.ingestion.spotify.transform import (
    build_spotify_account_source_candidates,
    build_spotify_event_candidates,
    parse_loaded_spotify_streaming_history_document,
    parse_spotify_streaming_history_document,
)

__all__ = [
    "LoadedSpotifyStreamingHistoryDocument",
    "ParsedSpotifyStreamingHistoryDocument",
    "ParsedSpotifyStreamRow",
    "SpotifyAccountSourceCandidate",
    "SpotifyDocumentCandidate",
    "SpotifyEventCandidate",
    "SpotifyIngestionResult",
    "SpotifyStreamingHistoryDocumentDescriptor",
    "SpotifyTransformError",
    "build_spotify_account_source_candidates",
    "build_spotify_event_candidates",
    "parse_loaded_spotify_streaming_history_document",
    "parse_spotify_streaming_history_document",
]
