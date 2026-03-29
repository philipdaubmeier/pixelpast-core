"""Service composition root for Spotify event ingestion."""

from __future__ import annotations

from pathlib import Path

from pixelpast.ingestion.service_base import SharedStagedIngestionServiceBase
from pixelpast.ingestion.spotify.connector import SpotifyConnector
from pixelpast.ingestion.spotify.contracts import SpotifyIngestionResult
from pixelpast.ingestion.spotify.lifecycle import SpotifyIngestionRunCoordinator
from pixelpast.ingestion.spotify.progress import (
    SpotifyIngestionProgressSnapshot,
    SpotifyIngestionProgressTracker,
)
from pixelpast.ingestion.spotify.staged import (
    SpotifyIngestionPersistenceScope,
    SpotifyStagedIngestionStrategy,
)
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


class SpotifyIngestionService(
    SharedStagedIngestionServiceBase[
        SpotifyConnector,
        SpotifyIngestionRunCoordinator,
        SpotifyStagedIngestionStrategy,
        SpotifyIngestionProgressTracker,
        SpotifyIngestionPersistenceScope,
        SpotifyIngestionResult,
    ]
):
    """Wire Spotify-specific collaborators into the staged ingestion runner."""

    def _build_default_connector(self) -> SpotifyConnector:
        return SpotifyConnector()

    def _build_default_lifecycle(self) -> SpotifyIngestionRunCoordinator:
        return SpotifyIngestionRunCoordinator()

    def _resolve_runtime_root(
        self,
        *,
        runtime: RuntimeContext,
        **kwargs: object,
    ) -> Path:
        configured_root = kwargs.get("root") or runtime.settings.spotify_root
        if configured_root is None:
            raise ValueError(
                "Spotify ingestion requires PIXELPAST_SPOTIFY_ROOT to be configured."
            )
        return configured_root.expanduser().resolve()

    def _build_strategy(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> SpotifyStagedIngestionStrategy:
        del runtime, resolved_root, kwargs
        return SpotifyStagedIngestionStrategy(connector=self._connector)

    def _build_progress_tracker(
        self,
        *,
        runtime: RuntimeContext,
        run_id: int,
        progress_callback: JobProgressCallback | None,
        **kwargs: object,
    ) -> SpotifyIngestionProgressTracker:
        del kwargs
        return SpotifyIngestionProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
            heartbeat_interval_seconds=self._heartbeat_interval_seconds,
            now_factory=self._now_factory,
            monotonic_factory=self._monotonic_factory,
        )

    def _build_persistence_scope(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
        **kwargs: object,
    ) -> SpotifyIngestionPersistenceScope:
        del resolved_root, kwargs
        return SpotifyIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
        )

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        root: Path | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> SpotifyIngestionResult:
        """Run staged Spotify ingestion and return the stable public result."""

        return self._ingest(
            runtime=runtime,
            root=root,
            progress_callback=progress_callback,
        )


__all__ = [
    "SpotifyIngestionProgressSnapshot",
    "SpotifyIngestionResult",
    "SpotifyIngestionService",
]
