"""Raw content loading for discovered Spotify streaming-history documents."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pixelpast.ingestion.spotify.contracts import SpotifyStreamingHistoryDocumentDescriptor

_TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252")


@dataclass(slots=True, frozen=True)
class SpotifyDocumentLoadProgress:
    """Represents one raw Spotify document load transition."""

    event: str
    document: SpotifyStreamingHistoryDocumentDescriptor
    document_index: int
    document_total: int


class SpotifyStreamingHistoryFetcher:
    """Load raw Spotify JSON text for discovered document descriptors."""

    def fetch_text_by_descriptor(
        self,
        *,
        documents: Sequence[SpotifyStreamingHistoryDocumentDescriptor],
        on_document_progress: (
            Callable[[SpotifyDocumentLoadProgress], None] | None
        ) = None,
    ) -> dict[SpotifyStreamingHistoryDocumentDescriptor, str]:
        """Return raw Spotify document text indexed by descriptor."""

        fetched_documents: dict[SpotifyStreamingHistoryDocumentDescriptor, str] = {}
        document_total = len(documents)
        for index, document in enumerate(documents, start=1):
            if on_document_progress is not None:
                on_document_progress(
                    SpotifyDocumentLoadProgress(
                        event="submitted",
                        document=document,
                        document_index=index,
                        document_total=document_total,
                    )
                )
            fetched_documents[document] = _decode_spotify_bytes(document.path.read_bytes())
            if on_document_progress is not None:
                on_document_progress(
                    SpotifyDocumentLoadProgress(
                        event="completed",
                        document=document,
                        document_index=index,
                        document_total=document_total,
                    )
                )
        return fetched_documents


def _decode_spotify_bytes(payload: bytes) -> str:
    for encoding in _TEXT_ENCODINGS:
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


__all__ = ["SpotifyDocumentLoadProgress", "SpotifyStreamingHistoryFetcher"]
