"""Spotify ingestion contracts and transform helpers."""

from pixelpast.ingestion.spotify.connector import SpotifyConnector
from pixelpast.ingestion.spotify.contracts import (
    LoadedSpotifyStreamingHistoryDocument,
    SpotifyAccountCandidate,
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
from pixelpast.ingestion.spotify.fetch import (
    SpotifyDocumentLoadProgress,
    SpotifyStreamingHistoryFetcher,
)
from pixelpast.ingestion.spotify.lifecycle import SpotifyIngestionRunCoordinator
from pixelpast.ingestion.spotify.persist import SpotifyAccountPersister
from pixelpast.ingestion.spotify.progress import (
    SpotifyIngestionProgressSnapshot,
    SpotifyIngestionProgressTracker,
)
from pixelpast.ingestion.spotify.service import SpotifyIngestionService
from pixelpast.ingestion.spotify.staged import (
    SpotifyIngestionPersistenceScope,
    SpotifyStagedIngestionStrategy,
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
    "SpotifyAccountCandidate",
    "LoadedSpotifyStreamingHistoryDocument",
    "SpotifyAccountDocumentGroup",
    "SpotifyAccountPersister",
    "SpotifyConnector",
    "ParsedSpotifyStreamingHistoryDocument",
    "ParsedSpotifyStreamRow",
    "SpotifyAccountSourceCandidate",
    "SpotifyDocumentLoadProgress",
    "SpotifyDocumentCandidate",
    "SpotifyEventCandidate",
    "SpotifyIngestionResult",
    "SpotifyIngestionPersistenceScope",
    "SpotifyIngestionProgressSnapshot",
    "SpotifyIngestionProgressTracker",
    "SpotifyIngestionRunCoordinator",
    "SpotifyIngestionService",
    "SpotifyStagedIngestionStrategy",
    "SpotifyStreamingHistoryDiscoveryResult",
    "SpotifyStreamingHistoryDocumentDescriptor",
    "SpotifyTransformError",
    "SpotifyStreamingHistoryDocumentDiscoverer",
    "SpotifyStreamingHistoryFetcher",
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
