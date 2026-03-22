"""Operational lifecycle helpers for Google Maps Timeline ingestion runs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineDocumentCandidate,
)
from pixelpast.ingestion.google_maps_timeline.persist import (
    GoogleMapsTimelineDocumentPersister,
)
from pixelpast.persistence.repositories import (
    EventRepository,
    JobRunRepository,
    SourceRepository,
)
from pixelpast.shared.progress import build_initial_job_progress_payload
from pixelpast.shared.runtime import RuntimeContext

GOOGLE_MAPS_TIMELINE_JOB_NAME = "google_maps_timeline"
GOOGLE_MAPS_TIMELINE_JOB_TYPE = "ingest"
GOOGLE_MAPS_TIMELINE_MODE = "full"
GOOGLE_MAPS_TIMELINE_INITIAL_PHASE = "initializing"


class GoogleMapsTimelineIngestionRunCoordinator:
    """Coordinate run bootstrap for Google Maps Timeline ingestion."""

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Persist a new Google Maps Timeline ingestion run."""

        session = runtime.session_factory()
        try:
            job_run = JobRunRepository(session).create(
                job_type=GOOGLE_MAPS_TIMELINE_JOB_TYPE,
                job=GOOGLE_MAPS_TIMELINE_JOB_NAME,
                mode=GOOGLE_MAPS_TIMELINE_MODE,
                phase=GOOGLE_MAPS_TIMELINE_INITIAL_PHASE,
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
        candidates: Sequence[GoogleMapsTimelineDocumentCandidate],
    ) -> int:
        """Return the source-scoped missing event count for export documents."""

        persister = GoogleMapsTimelineDocumentPersister(
            source_repository=source_repository,
            event_repository=event_repository,
        )
        return sum(
            persister.count_missing_from_source(candidate=candidate)
            for candidate in candidates
        )


__all__ = [
    "GOOGLE_MAPS_TIMELINE_INITIAL_PHASE",
    "GOOGLE_MAPS_TIMELINE_JOB_NAME",
    "GOOGLE_MAPS_TIMELINE_JOB_TYPE",
    "GOOGLE_MAPS_TIMELINE_MODE",
    "GoogleMapsTimelineIngestionRunCoordinator",
]
