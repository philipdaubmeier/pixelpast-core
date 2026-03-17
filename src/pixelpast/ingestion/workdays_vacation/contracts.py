"""Public data contracts for workdays-vacation ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class WorkdaysVacationWorkbookDescriptor:
    """One discovered workbook intake unit."""

    path: Path

    @property
    def origin_path(self) -> Path:
        """Return the normalized filesystem path for the workbook."""

        return self.path.expanduser().resolve()

    @property
    def origin_label(self) -> str:
        """Return the deterministic human-readable workbook identifier."""

        return self.origin_path.as_posix()


@dataclass(slots=True, frozen=True)
class ParsedWorkdaysVacationWorkbook:
    """Parsed workbook-level metadata prior to canonical transformation."""

    descriptor: WorkdaysVacationWorkbookDescriptor
    sheet_names: tuple[str, ...]
    legend_entries: tuple["WorkdaysVacationLegendEntry", ...]
    day_entries: tuple["ParsedWorkdaysVacationDay", ...]
    skipped_day_warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class WorkdaysVacationLegendEntry:
    """One parsed legend row from the workbook."""

    code: str
    description: str | None
    color_value: str


@dataclass(slots=True, frozen=True)
class ParsedWorkdaysVacationDay:
    """One populated workbook day cell resolved into calendar coordinates."""

    represented_date: date
    short_code: str
    color_value: str
    legend_description: str | None
    worksheet_row: int
    worksheet_column: str


@dataclass(slots=True, frozen=True)
class WorkdaysVacationSourceCandidate:
    """Canonical source candidate derived from one workbook."""

    type: str
    name: str | None
    external_id: str | None
    config_json: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class WorkdaysVacationEventCandidate:
    """Canonical event candidate derived from one workbook row."""

    source_external_id: str | None
    external_event_id: str | None
    type: str
    timestamp_start: datetime
    timestamp_end: datetime | None
    title: str | None
    summary: str | None
    raw_payload: dict[str, Any] | None
    derived_payload: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class WorkdaysVacationWorkbookCandidate:
    """One persistable workbook candidate for staged ingestion."""

    workbook: WorkdaysVacationWorkbookDescriptor
    source: WorkdaysVacationSourceCandidate
    events: tuple[WorkdaysVacationEventCandidate, ...]
    skipped_event_count: int = 0


@dataclass(slots=True, frozen=True)
class WorkdaysVacationTransformError:
    """Represents one non-fatal workbook transform failure."""

    workbook: WorkdaysVacationWorkbookDescriptor
    message: str


@dataclass(slots=True, frozen=True)
class WorkdaysVacationIngestionResult:
    """Summary of a completed workdays-vacation ingestion run."""

    run_id: int
    processed_workbook_count: int
    persisted_source_count: int
    persisted_event_count: int
    error_count: int
    status: str
    transform_errors: tuple[WorkdaysVacationTransformError, ...] = ()


__all__ = [
    "ParsedWorkdaysVacationDay",
    "ParsedWorkdaysVacationWorkbook",
    "WorkdaysVacationEventCandidate",
    "WorkdaysVacationIngestionResult",
    "WorkdaysVacationLegendEntry",
    "WorkdaysVacationSourceCandidate",
    "WorkdaysVacationTransformError",
    "WorkdaysVacationWorkbookCandidate",
    "WorkdaysVacationWorkbookDescriptor",
]
