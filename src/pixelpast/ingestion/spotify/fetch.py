"""Raw content loading for discovered Spotify streaming-history documents."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from zipfile import BadZipFile, ZipFile

from pixelpast.ingestion.spotify.contracts import (
    SpotifyStreamingHistoryDocumentDescriptor,
)

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
            fetched_documents[document] = self._fetch_document_text(document=document)
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

    def _fetch_document_text(
        self,
        *,
        document: SpotifyStreamingHistoryDocumentDescriptor,
    ) -> str:
        if document.archive_member_path is None:
            return _decode_spotify_bytes(document.path.read_bytes())
        return self._read_archive_member(document=document)

    def _read_archive_member(
        self,
        *,
        document: SpotifyStreamingHistoryDocumentDescriptor,
    ) -> str:
        try:
            with ZipFile(document.path) as archive:
                try:
                    member_bytes = archive.read(document.archive_member_path)
                except KeyError as error:
                    raise ValueError(
                        "Spotify archive member does not exist: "
                        f"{document.origin_label}"
                    ) from error
        except BadZipFile as error:
            raise ValueError(f"Spotify zip file is invalid: {document.path}") from error

        return _decode_spotify_bytes(member_bytes)


def _decode_spotify_bytes(payload: bytes) -> str:
    for encoding in _TEXT_ENCODINGS:
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


__all__ = ["SpotifyDocumentLoadProgress", "SpotifyStreamingHistoryFetcher"]
