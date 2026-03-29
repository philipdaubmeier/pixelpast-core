"""Operational lifecycle helpers for Spotify ingestion runs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.spotify.contracts import SpotifyAccountCandidate
from pixelpast.ingestion.spotify.persist import SpotifyAccountPersister
from pixelpast.persistence.repositories import (
    EventRepository,
    SourceRepository,
)
from pixelpast.shared.job_run_coordinator import JobRunCoordinatorBase
from pixelpast.shared.runtime import RuntimeContext

SPOTIFY_JOB_NAME = "spotify"
SPOTIFY_JOB_TYPE = "ingest"
SPOTIFY_MODE = "full"
SPOTIFY_INITIAL_PHASE = "initializing"


class SpotifyIngestionRunCoordinator(JobRunCoordinatorBase):
    """Coordinate run bootstrap and reconciliation for Spotify ingestion."""

    job_type = SPOTIFY_JOB_TYPE
    job_name = SPOTIFY_JOB_NAME
    mode = SPOTIFY_MODE
    initial_phase = SPOTIFY_INITIAL_PHASE

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Persist a new Spotify ingestion run."""

        return self._create_run(runtime=runtime, resolved_root=resolved_root)

    def _include_root_path_in_payload(self) -> bool:
        return True

    def count_missing_from_source(
        self,
        *,
        source_repository: SourceRepository,
        event_repository: EventRepository,
        candidates: Sequence[SpotifyAccountCandidate],
    ) -> int:
        """Return the source-scoped missing event count for Spotify accounts."""

        persister = SpotifyAccountPersister(
            source_repository=source_repository,
            event_repository=event_repository,
        )
        return sum(
            persister.count_missing_from_source(candidate=candidate)
            for candidate in candidates
        )


__all__ = [
    "SPOTIFY_INITIAL_PHASE",
    "SPOTIFY_JOB_NAME",
    "SPOTIFY_JOB_TYPE",
    "SPOTIFY_MODE",
    "SpotifyIngestionRunCoordinator",
]
