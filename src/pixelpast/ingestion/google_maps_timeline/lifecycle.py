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
    SourceRepository,
)
from pixelpast.shared.job_run_coordinator import JobRunCoordinatorBase
from pixelpast.shared.runtime import RuntimeContext

GOOGLE_MAPS_TIMELINE_JOB_NAME = "google_maps_timeline"
GOOGLE_MAPS_TIMELINE_JOB_TYPE = "ingest"
GOOGLE_MAPS_TIMELINE_MODE = "full"
GOOGLE_MAPS_TIMELINE_INITIAL_PHASE = "initializing"


class GoogleMapsTimelineIngestionRunCoordinator(JobRunCoordinatorBase):
    """Coordinate run bootstrap for Google Maps Timeline ingestion."""

    job_type = GOOGLE_MAPS_TIMELINE_JOB_TYPE
    job_name = GOOGLE_MAPS_TIMELINE_JOB_NAME
    mode = GOOGLE_MAPS_TIMELINE_MODE
    initial_phase = GOOGLE_MAPS_TIMELINE_INITIAL_PHASE

    def create_run(
        self,
        *,
        runtime: RuntimeContext,
        resolved_root: Path,
    ) -> int:
        """Persist a new Google Maps Timeline ingestion run."""

        return self._create_run(runtime=runtime, resolved_root=resolved_root)

    def _include_root_path_in_payload(self) -> bool:
        return True

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
