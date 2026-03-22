"""Google Maps Timeline adapters for the reusable staged ingestion runner."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.google_maps_timeline.connector import (
    GoogleMapsTimelineConnector,
)
from pixelpast.ingestion.google_maps_timeline.contracts import (
    GoogleMapsTimelineDocumentCandidate,
    GoogleMapsTimelineDocumentDescriptor,
    GoogleMapsTimelineIngestionResult,
    GoogleMapsTimelineTransformError,
    LoadedGoogleMapsTimelineExportDocument,
)
from pixelpast.ingestion.google_maps_timeline.lifecycle import (
    GoogleMapsTimelineIngestionRunCoordinator,
)
from pixelpast.ingestion.google_maps_timeline.persist import (
    GoogleMapsTimelineDocumentPersister,
)
from pixelpast.persistence.repositories import EventRepository, SourceRepository
from pixelpast.shared.runtime import RuntimeContext


class GoogleMapsTimelineIngestionPersistenceScope:
    """Wrap the Google Maps Timeline persistence transaction boundary."""

    def __init__(
        self,
        *,
        runtime: RuntimeContext,
        lifecycle: GoogleMapsTimelineIngestionRunCoordinator,
    ) -> None:
        session = runtime.session_factory()
        self._session = session
        self._lifecycle = lifecycle
        self._source_repository = SourceRepository(session)
        self._event_repository = EventRepository(session)
        self._persister = GoogleMapsTimelineDocumentPersister(
            source_repository=self._source_repository,
            event_repository=self._event_repository,
        )

    @property
    def persisted_source_count(self) -> int:
        return self._persister.persisted_source_count

    @property
    def persisted_event_count(self) -> int:
        return self._persister.persisted_event_count

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_units: Sequence[GoogleMapsTimelineDocumentDescriptor],
        candidates: Sequence[GoogleMapsTimelineDocumentCandidate],
    ) -> int:
        del resolved_root, discovered_units
        return self._lifecycle.count_missing_from_source(
            source_repository=self._source_repository,
            event_repository=self._event_repository,
            candidates=candidates,
        )

    def persist(self, *, candidate: GoogleMapsTimelineDocumentCandidate) -> str:
        return self._persister.persist(candidate=candidate)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()


class GoogleMapsTimelineStagedIngestionStrategy:
    """Bind the Google Maps Timeline connector to the staged runner contract."""

    def __init__(self, *, connector: GoogleMapsTimelineConnector) -> None:
        self._connector = connector

    def discover_units(
        self,
        *,
        root: Path,
        on_unit_discovered,
    ) -> Sequence[GoogleMapsTimelineDocumentDescriptor]:
        return self._connector.discover_documents(
            root,
            on_document_discovered=on_unit_discovered,
        )

    def fetch_payloads(
        self,
        *,
        units: Sequence[GoogleMapsTimelineDocumentDescriptor],
        on_batch_progress,
    ) -> dict[GoogleMapsTimelineDocumentDescriptor, LoadedGoogleMapsTimelineExportDocument]:
        loaded_documents = self._connector.fetch_documents(
            documents=units,
            on_document_progress=on_batch_progress,
        )
        return {
            loaded_document.descriptor: loaded_document
            for loaded_document in loaded_documents
        }

    def build_candidate(
        self,
        *,
        root: Path,
        unit: GoogleMapsTimelineDocumentDescriptor,
        fetched_payloads: dict[
            GoogleMapsTimelineDocumentDescriptor,
            LoadedGoogleMapsTimelineExportDocument,
        ],
    ) -> GoogleMapsTimelineDocumentCandidate:
        del root
        parsed_document = self._connector.parse_loaded_document(fetched_payloads[unit])
        return self._connector.build_document_candidate(parsed_document)

    def build_transform_error(
        self,
        *,
        unit: GoogleMapsTimelineDocumentDescriptor,
        error: Exception,
    ) -> GoogleMapsTimelineTransformError:
        return self._connector.build_transform_error(document=unit, error=error)

    def describe_unit(self, *, unit: GoogleMapsTimelineDocumentDescriptor) -> str:
        return unit.origin_label

    def build_result(
        self,
        *,
        run_id: int,
        progress,
        transform_errors: Sequence[GoogleMapsTimelineTransformError],
    ) -> GoogleMapsTimelineIngestionResult:
        status = "partial_failure" if transform_errors else "completed"
        counters = progress.counters
        return GoogleMapsTimelineIngestionResult(
            run_id=run_id,
            processed_document_count=counters.persisted_document_count,
            persisted_source_count=counters.persisted_source_count,
            persisted_event_count=counters.persisted_event_count,
            error_count=len(transform_errors),
            status=status,
        )


__all__ = [
    "GoogleMapsTimelineIngestionPersistenceScope",
    "GoogleMapsTimelineStagedIngestionStrategy",
]
