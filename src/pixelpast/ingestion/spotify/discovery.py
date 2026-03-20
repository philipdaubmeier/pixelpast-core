"""Filesystem discovery and account grouping for Spotify ingestion."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path

from pixelpast.ingestion.spotify.contracts import (
    ParsedSpotifyStreamingHistoryDocument,
    ParsedSpotifyStreamRow,
    SpotifyAccountDocumentGroup,
    SpotifyStreamingHistoryDiscoveryResult,
    SpotifyStreamingHistoryDocumentDescriptor,
)
from pixelpast.ingestion.spotify.transform import build_spotify_source_external_id
from pixelpast.shared.settings import Settings

_SUPPORTED_FILE_PREFIXES = ("streaming_history_audio", "streaming_history_video")


def resolve_spotify_ingestion_root(
    *,
    settings: Settings,
    root: Path | None = None,
) -> Path:
    """Return the configured Spotify intake root or raise a clear error."""

    configured_root = root or settings.spotify_root
    if configured_root is None:
        raise ValueError(
            "Spotify ingestion requires PIXELPAST_SPOTIFY_ROOT to be configured."
        )
    return configured_root.expanduser().resolve()


class SpotifyStreamingHistoryDocumentDiscoverer:
    """Discover supported Spotify streaming-history JSON files from one root."""

    def discover_documents(
        self,
        root: Path,
        *,
        on_document_discovered: (
            Callable[[SpotifyStreamingHistoryDocumentDescriptor, int], None] | None
        ) = None,
    ) -> SpotifyStreamingHistoryDiscoveryResult:
        """Return supported Spotify streaming-history documents beneath one root."""

        resolved_root = root.expanduser().resolve()
        if not resolved_root.exists():
            raise ValueError(f"Spotify root does not exist: {resolved_root}")

        documents, skipped_json_file_count = self._discover_from_root(root=resolved_root)
        if on_document_discovered is not None:
            for index, document in enumerate(documents, start=1):
                on_document_discovered(document, index)
        return SpotifyStreamingHistoryDiscoveryResult(
            documents=documents,
            skipped_json_file_count=skipped_json_file_count,
        )

    def _discover_from_root(
        self,
        *,
        root: Path,
    ) -> tuple[tuple[SpotifyStreamingHistoryDocumentDescriptor, ...], int]:
        if root.is_file():
            return self._discover_from_file(path=root)
        if root.is_dir():
            return self._discover_from_directory(root=root)
        raise ValueError(f"Spotify root is neither file nor directory: {root}")

    def _discover_from_directory(
        self,
        *,
        root: Path,
    ) -> tuple[tuple[SpotifyStreamingHistoryDocumentDescriptor, ...], int]:
        documents: list[SpotifyStreamingHistoryDocumentDescriptor] = []
        skipped_json_file_count = 0
        for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
            if not path.is_file() or path.suffix.lower() != ".json":
                continue
            if self._is_supported_streaming_history_file(path):
                documents.append(SpotifyStreamingHistoryDocumentDescriptor(path=path))
                continue
            skipped_json_file_count += 1
        return tuple(documents), skipped_json_file_count

    def _discover_from_file(
        self,
        *,
        path: Path,
    ) -> tuple[tuple[SpotifyStreamingHistoryDocumentDescriptor, ...], int]:
        if path.suffix.lower() != ".json":
            raise ValueError(f"Spotify root is not supported: {path}")
        if not self._is_supported_streaming_history_file(path):
            raise ValueError(
                "Spotify root is not a supported streaming-history JSON file: "
                f"{path}"
            )
        return (SpotifyStreamingHistoryDocumentDescriptor(path=path),), 0

    def _is_supported_streaming_history_file(self, path: Path) -> bool:
        normalized_name = path.name.casefold()
        return any(
            normalized_name.startswith(prefix) for prefix in _SUPPORTED_FILE_PREFIXES
        )


def group_spotify_documents_by_account(
    documents: Iterable[ParsedSpotifyStreamingHistoryDocument],
) -> tuple[SpotifyAccountDocumentGroup, ...]:
    """Group parsed Spotify documents into account-scoped replacement sets."""

    documents_by_username: dict[str, dict[str, ParsedSpotifyStreamingHistoryDocument]] = (
        defaultdict(dict)
    )
    rows_by_username: dict[str, list[ParsedSpotifyStreamRow]] = defaultdict(list)

    for document in sorted(
        documents,
        key=lambda candidate: candidate.descriptor.origin_label,
    ):
        for row in document.rows:
            normalized_username = row.normalized_username
            if normalized_username is None:
                continue
            documents_by_username[normalized_username][
                document.descriptor.origin_label
            ] = document
            rows_by_username[normalized_username].append(row)

    grouped_documents: list[SpotifyAccountDocumentGroup] = []
    for normalized_username in sorted(documents_by_username):
        grouped_documents.append(
            SpotifyAccountDocumentGroup(
                normalized_username=normalized_username,
                source_external_id=build_spotify_source_external_id(normalized_username),
                documents=tuple(
                    documents_by_username[normalized_username][origin_label]
                    for origin_label in sorted(documents_by_username[normalized_username])
                ),
                rows=tuple(rows_by_username[normalized_username]),
            )
        )
    return tuple(grouped_documents)


__all__ = [
    "SpotifyStreamingHistoryDocumentDiscoverer",
    "group_spotify_documents_by_account",
    "resolve_spotify_ingestion_root",
]
