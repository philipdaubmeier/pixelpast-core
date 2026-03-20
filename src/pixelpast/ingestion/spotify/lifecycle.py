"""Operational lifecycle helpers for Spotify ingestion runs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.spotify.contracts import SpotifyAccountCandidate
from pixelpast.ingestion.spotify.persist import SpotifyAccountPersister
from pixelpast.persistence.repositories import (
    EventRepository,
    JobRunRepository,
    SourceRepository,
)
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import RuntimeContext

SPOTIFY_JOB_NAME = "spotify"
SPOTIFY_JOB_TYPE = "ingest"
SPOTIFY_MODE = "full"
SPOTIFY_INITIAL_PHASE = "initializing"


class SpotifyIngestionRunCoordinator:
    """Coordinate run bootstrap and reconciliation for Spotify ingestion."""

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Persist a new Spotify ingestion run."""

        session = runtime.session_factory()
        try:
            job_run = JobRunRepository(session).create(
                job_type=SPOTIFY_JOB_TYPE,
                job=SPOTIFY_JOB_NAME,
                mode=SPOTIFY_MODE,
                phase=SPOTIFY_INITIAL_PHASE,
                progress_json={
                    **build_initial_job_progress_payload(),
                    "root_path": resolved_root.as_posix(),
                },
            )
            session.commit()
            return job_run.id
        finally:
            session.close()

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
