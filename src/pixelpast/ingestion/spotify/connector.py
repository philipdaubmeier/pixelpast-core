"""Composition facade for Spotify discovery, fetch, and transform."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from pixelpast.ingestion.spotify.contracts import (
    ParsedSpotifyStreamingHistoryDocument,
    SpotifyAccountCandidate,
    SpotifyAccountDocumentGroup,
    SpotifyStreamingHistoryDiscoveryResult,
    SpotifyStreamingHistoryDocumentDescriptor,
    SpotifyTransformError,
)
from pixelpast.ingestion.spotify.discovery import SpotifyStreamingHistoryDocumentDiscoverer
from pixelpast.ingestion.spotify.fetch import (
    SpotifyDocumentLoadProgress,
    SpotifyStreamingHistoryFetcher,
)
from pixelpast.ingestion.spotify.transform import (
    build_spotify_account_source_candidates,
    build_spotify_event_candidates_for_documents,
    parse_spotify_streaming_history_document,
)


class SpotifyConnector:
    """Facade that composes Spotify discovery, fetch, and transform stages."""

    def __init__(
        self,
        *,
        document_discoverer: SpotifyStreamingHistoryDocumentDiscoverer | None = None,
        document_fetcher: SpotifyStreamingHistoryFetcher | None = None,
    ) -> None:
        self._document_discoverer = (
            document_discoverer
            if document_discoverer is not None
            else SpotifyStreamingHistoryDocumentDiscoverer()
        )
        self._document_fetcher = (
            document_fetcher
            if document_fetcher is not None
            else SpotifyStreamingHistoryFetcher()
        )

    def discover_documents(
        self,
        root: Path,
        *,
        on_document_discovered: (
            Callable[[SpotifyStreamingHistoryDocumentDescriptor, int], None] | None
        ) = None,
    ) -> SpotifyStreamingHistoryDiscoveryResult:
        """Delegate document discovery to the dedicated discoverer component."""

        return self._document_discoverer.discover_documents(
            root,
            on_document_discovered=on_document_discovered,
        )

    def fetch_text_by_descriptor(
        self,
        *,
        documents: Sequence[SpotifyStreamingHistoryDocumentDescriptor],
        on_document_progress: (
            Callable[[SpotifyDocumentLoadProgress], None] | None
        ) = None,
    ) -> dict[SpotifyStreamingHistoryDocumentDescriptor, str]:
        """Load raw Spotify JSON text for the discovered document set."""

        return self._document_fetcher.fetch_text_by_descriptor(
            documents=documents,
            on_document_progress=on_document_progress,
        )

    def parse_document(
        self,
        *,
        document: SpotifyStreamingHistoryDocumentDescriptor,
        text: str,
    ) -> ParsedSpotifyStreamingHistoryDocument:
        """Parse one discovered Spotify document."""

        return parse_spotify_streaming_history_document(
            descriptor=document,
            text=text,
        )

    def build_account_candidate(
        self,
        *,
        account_group: SpotifyAccountDocumentGroup,
    ) -> SpotifyAccountCandidate:
        """Build one persistable account-scoped Spotify replacement set."""

        source_candidates = build_spotify_account_source_candidates(account_group.documents)
        if len(source_candidates) != 1:
            raise ValueError(
                "Spotify account group must resolve to exactly one source candidate."
            )
        return SpotifyAccountCandidate(
            normalized_username=account_group.normalized_username,
            documents=tuple(
                document.descriptor for document in account_group.documents
            ),
            source=source_candidates[0],
            events=build_spotify_event_candidates_for_documents(account_group.documents),
        )

    def build_transform_error(
        self,
        *,
        document: SpotifyStreamingHistoryDocumentDescriptor,
        error: Exception,
    ) -> SpotifyTransformError:
        """Translate one analysis failure into the stable Spotify error contract."""

        return SpotifyTransformError(document=document, message=str(error))


__all__ = ["SpotifyConnector"]
