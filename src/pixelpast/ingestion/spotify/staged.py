"""Spotify-specific adapters for the reusable staged ingestion runner."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pixelpast.ingestion.spotify.connector import SpotifyConnector
from pixelpast.ingestion.spotify.contracts import (
    ParsedSpotifyStreamingHistoryDocument,
    SpotifyAccountCandidate,
    SpotifyIngestionResult,
    SpotifyStreamingHistoryDocumentDescriptor,
    SpotifyTransformError,
)
from pixelpast.ingestion.spotify.discovery import group_spotify_documents_by_account
from pixelpast.ingestion.spotify.lifecycle import SpotifyIngestionRunCoordinator
from pixelpast.ingestion.spotify.persist import SpotifyAccountPersister
from pixelpast.ingestion.spotify.progress import SpotifyIngestionProgressTracker
from pixelpast.persistence.repositories import EventRepository, SourceRepository
from pixelpast.shared.runtime import RuntimeContext


class SpotifyIngestionPersistenceScope:
    """Wrap the Spotify persistence transaction boundary for the staged runner."""

    def __init__(
        self,
        *,
        runtime: RuntimeContext,
        lifecycle: SpotifyIngestionRunCoordinator,
    ) -> None:
        session = runtime.session_factory()
        self._session = session
        self._lifecycle = lifecycle
        self._source_repository = SourceRepository(session)
        self._event_repository = EventRepository(session)
        self._persister = SpotifyAccountPersister(
            source_repository=self._source_repository,
            event_repository=self._event_repository,
        )

    def count_missing_from_source(
        self,
        *,
        resolved_root: Path,
        discovered_units: Sequence[SpotifyStreamingHistoryDocumentDescriptor],
        candidates: Sequence[SpotifyAccountCandidate],
    ) -> int:
        del resolved_root, discovered_units
        return self._lifecycle.count_missing_from_source(
            source_repository=self._source_repository,
            event_repository=self._event_repository,
            candidates=candidates,
        )

    def persist(self, *, candidate: SpotifyAccountCandidate) -> str:
        return self._persister.persist(candidate=candidate)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()


class SpotifyStagedIngestionStrategy:
    """Bind the Spotify connector to the generic staged runner contract."""

    def __init__(self, *, connector: SpotifyConnector) -> None:
        self._connector = connector
        self.skipped_json_file_count = 0
        self._prepared = False
        self._candidate_by_origin_label: dict[str, SpotifyAccountCandidate | None] = {}
        self._error_by_origin_label: dict[str, Exception] = {}

    def discover_units(
        self,
        *,
        root: Path,
        on_unit_discovered,
    ) -> Sequence[SpotifyStreamingHistoryDocumentDescriptor]:
        self._prepared = False
        self._candidate_by_origin_label.clear()
        self._error_by_origin_label.clear()
        discovery_result = self._connector.discover_documents(
            root,
            on_document_discovered=on_unit_discovered,
        )
        self.skipped_json_file_count = discovery_result.skipped_json_file_count
        return discovery_result.documents

    def fetch_payloads(
        self,
        *,
        units: Sequence[SpotifyStreamingHistoryDocumentDescriptor],
        on_batch_progress,
    ) -> dict[SpotifyStreamingHistoryDocumentDescriptor, str]:
        return self._connector.fetch_text_by_descriptor(
            documents=units,
            on_document_progress=on_batch_progress,
        )

    def build_candidate(
        self,
        *,
        root: Path,
        unit: SpotifyStreamingHistoryDocumentDescriptor,
        fetched_payloads: dict[SpotifyStreamingHistoryDocumentDescriptor, str],
    ) -> SpotifyAccountCandidate | None:
        del root
        self._prepare_account_candidates(
            units=list(fetched_payloads),
            fetched_payloads=fetched_payloads,
        )
        origin_label = unit.origin_label
        if origin_label in self._error_by_origin_label:
            raise self._error_by_origin_label[origin_label]
        return self._candidate_by_origin_label.get(origin_label)

    def build_transform_error(
        self,
        *,
        unit: SpotifyStreamingHistoryDocumentDescriptor,
        error: Exception,
    ) -> SpotifyTransformError:
        return self._connector.build_transform_error(document=unit, error=error)

    def describe_unit(self, *, unit: SpotifyStreamingHistoryDocumentDescriptor) -> str:
        return unit.origin_label

    def build_result(
        self,
        *,
        run_id: int,
        progress: SpotifyIngestionProgressTracker,
        transform_errors: Sequence[SpotifyTransformError],
    ) -> SpotifyIngestionResult:
        status = "partial_failure" if transform_errors else "completed"
        counters = progress.counters
        return SpotifyIngestionResult(
            run_id=run_id,
            processed_document_count=counters.analyzed_file_count,
            persisted_source_count=counters.persisted_source_count,
            persisted_event_count=counters.persisted_event_count,
            error_count=len(transform_errors),
            status=status,
            skipped_json_file_count=self.skipped_json_file_count,
            transform_errors=tuple(transform_errors),
        )

    def _prepare_account_candidates(
        self,
        *,
        units: Sequence[SpotifyStreamingHistoryDocumentDescriptor],
        fetched_payloads: dict[SpotifyStreamingHistoryDocumentDescriptor, str],
    ) -> None:
        if self._prepared:
            return

        parsed_documents: list[ParsedSpotifyStreamingHistoryDocument] = []
        for unit in units:
            try:
                parsed_documents.append(
                    self._connector.parse_document(
                        document=unit,
                        text=fetched_payloads[unit],
                    )
                )
            except Exception as error:
                self._error_by_origin_label[unit.origin_label] = error

        for account_group in group_spotify_documents_by_account(parsed_documents):
            representative_origin_label = account_group.documents[0].descriptor.origin_label
            self._candidate_by_origin_label[representative_origin_label] = (
                self._connector.build_account_candidate(account_group=account_group)
            )
            for document in account_group.documents[1:]:
                self._candidate_by_origin_label[document.descriptor.origin_label] = None

        for unit in units:
            self._candidate_by_origin_label.setdefault(unit.origin_label, None)

        self._prepared = True


__all__ = [
    "SpotifyIngestionPersistenceScope",
    "SpotifyStagedIngestionStrategy",
]
