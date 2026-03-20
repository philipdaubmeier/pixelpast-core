"""Service composition root for Spotify event ingestion."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import monotonic

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
from pixelpast.ingestion.staged import StagedIngestionRunner
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext

_HEARTBEAT_INTERVAL_SECONDS = 10.0


class SpotifyIngestionService:
    """Wire Spotify-specific collaborators into the staged ingestion runner."""

    def __init__(
        self,
        connector: SpotifyConnector | None = None,
        lifecycle: SpotifyIngestionRunCoordinator | None = None,
        *,
        heartbeat_interval_seconds: float = _HEARTBEAT_INTERVAL_SECONDS,
        now_factory: Callable[[], datetime] | None = None,
        monotonic_factory: Callable[[], float] | None = None,
    ) -> None:
        self._connector = connector or SpotifyConnector()
        self._lifecycle = lifecycle or SpotifyIngestionRunCoordinator()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._now_factory = now_factory
        self._monotonic_factory = monotonic_factory or monotonic
        self._runner = StagedIngestionRunner(
            strategy=SpotifyStagedIngestionStrategy(connector=self._connector)
        )

    def ingest(
        self,
        *,
        runtime: RuntimeContext,
        root: Path | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> SpotifyIngestionResult:
        """Run staged Spotify ingestion and return the stable public result."""

        configured_root = root or runtime.settings.spotify_root
        if configured_root is None:
            raise ValueError(
                "Spotify ingestion requires PIXELPAST_SPOTIFY_ROOT to be configured."
            )

        resolved_root = configured_root.expanduser().resolve()
        run_id = self._lifecycle.create_run(
            runtime=runtime,
            resolved_root=resolved_root,
        )
        progress = SpotifyIngestionProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
            heartbeat_interval_seconds=self._heartbeat_interval_seconds,
            now_factory=self._now_factory,
            monotonic_factory=self._monotonic_factory,
        )
        persistence = SpotifyIngestionPersistenceScope(
            runtime=runtime,
            lifecycle=self._lifecycle,
        )
        return self._runner.run(
            resolved_root=resolved_root,
            run_id=run_id,
            progress=progress,
            persistence=persistence,
        )


__all__ = [
    "SpotifyIngestionProgressSnapshot",
    "SpotifyIngestionResult",
    "SpotifyIngestionService",
]
