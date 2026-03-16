"""Workdays-vacation ingestion contracts and transform helpers."""

from pixelpast.ingestion.workdays_vacation.connector import WorkdaysVacationConnector
from pixelpast.ingestion.workdays_vacation.contracts import (
    ParsedWorkdaysVacationDay,
    ParsedWorkdaysVacationWorkbook,
    WorkdaysVacationEventCandidate,
    WorkdaysVacationIngestionResult,
    WorkdaysVacationLegendEntry,
    WorkdaysVacationSourceCandidate,
    WorkdaysVacationTransformError,
    WorkdaysVacationWorkbookCandidate,
    WorkdaysVacationWorkbookDescriptor,
)
from pixelpast.ingestion.workdays_vacation.discovery import (
    WorkdaysVacationWorkbookDiscoverer,
)
from pixelpast.ingestion.workdays_vacation.fetch import (
    WorkdaysVacationWorkbookFetcher,
    WorkdaysVacationWorkbookLoadProgress,
)
from pixelpast.ingestion.workdays_vacation.lifecycle import (
    WorkdaysVacationIngestionRunCoordinator,
)
from pixelpast.ingestion.workdays_vacation.persist import (
    WorkdaysVacationWorkbookPersister,
)
from pixelpast.ingestion.workdays_vacation.progress import (
    WorkdaysVacationIngestionProgressSnapshot,
    WorkdaysVacationIngestionProgressTracker,
)
from pixelpast.ingestion.workdays_vacation.service import (
    WorkdaysVacationIngestionService,
)
from pixelpast.ingestion.workdays_vacation.staged import (
    WorkdaysVacationIngestionPersistenceScope,
    WorkdaysVacationStagedIngestionStrategy,
)
from pixelpast.ingestion.workdays_vacation.transform import (
    build_workdays_vacation_event_candidates,
    build_workdays_vacation_source_candidate,
    parse_workdays_vacation_workbook,
)

__all__ = [
    "ParsedWorkdaysVacationDay",
    "ParsedWorkdaysVacationWorkbook",
    "WorkdaysVacationConnector",
    "WorkdaysVacationEventCandidate",
    "WorkdaysVacationIngestionPersistenceScope",
    "WorkdaysVacationIngestionProgressSnapshot",
    "WorkdaysVacationIngestionProgressTracker",
    "WorkdaysVacationIngestionResult",
    "WorkdaysVacationIngestionRunCoordinator",
    "WorkdaysVacationIngestionService",
    "WorkdaysVacationLegendEntry",
    "WorkdaysVacationSourceCandidate",
    "WorkdaysVacationStagedIngestionStrategy",
    "WorkdaysVacationTransformError",
    "WorkdaysVacationWorkbookCandidate",
    "WorkdaysVacationWorkbookDescriptor",
    "WorkdaysVacationWorkbookDiscoverer",
    "WorkdaysVacationWorkbookFetcher",
    "WorkdaysVacationWorkbookLoadProgress",
    "WorkdaysVacationWorkbookPersister",
    "build_workdays_vacation_event_candidates",
    "build_workdays_vacation_source_candidate",
    "parse_workdays_vacation_workbook",
]
