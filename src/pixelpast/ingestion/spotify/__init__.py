"""Spotify ingestion contracts and transform helpers."""

from pixelpast.ingestion.spotify.contracts import (
    LoadedSpotifyStreamingHistoryDocument,
    SpotifyAccountDocumentGroup,
    ParsedSpotifyStreamingHistoryDocument,
    ParsedSpotifyStreamRow,
    SpotifyAccountSourceCandidate,
    SpotifyDocumentCandidate,
    SpotifyEventCandidate,
    SpotifyIngestionResult,
    SpotifyStreamingHistoryDiscoveryResult,
    SpotifyStreamingHistoryDocumentDescriptor,
    SpotifyTransformError,
)
from pixelpast.ingestion.spotify.discovery import (
    SpotifyStreamingHistoryDocumentDiscoverer,
    group_spotify_documents_by_account,
    resolve_spotify_ingestion_root,
)
from pixelpast.ingestion.spotify.transform import (
    build_spotify_account_source_candidates,
    build_spotify_document_candidate,
    build_spotify_event_candidates,
    build_spotify_event_candidates_for_documents,
    build_spotify_source_external_id,
    parse_loaded_spotify_streaming_history_document,
    parse_spotify_streaming_history_document,
)

__all__ = [
    "LoadedSpotifyStreamingHistoryDocument",
    "SpotifyAccountDocumentGroup",
    "ParsedSpotifyStreamingHistoryDocument",
    "ParsedSpotifyStreamRow",
    "SpotifyAccountSourceCandidate",
    "SpotifyDocumentCandidate",
    "SpotifyEventCandidate",
    "SpotifyIngestionResult",
    "SpotifyStreamingHistoryDiscoveryResult",
    "SpotifyStreamingHistoryDocumentDescriptor",
    "SpotifyTransformError",
    "SpotifyStreamingHistoryDocumentDiscoverer",
    "build_spotify_account_source_candidates",
    "build_spotify_document_candidate",
    "build_spotify_event_candidates",
    "build_spotify_event_candidates_for_documents",
    "build_spotify_source_external_id",
    "group_spotify_documents_by_account",
    "parse_loaded_spotify_streaming_history_document",
    "parse_spotify_streaming_history_document",
    "resolve_spotify_ingestion_root",
]
