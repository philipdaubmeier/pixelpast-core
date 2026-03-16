"""Workbook parsing and canonical transformation helpers."""

from __future__ import annotations

import hashlib
import io
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pixelpast.ingestion.workdays_vacation.contracts import (
    ParsedWorkdaysVacationWorkbook,
    WorkdaysVacationEventCandidate,
    WorkdaysVacationSourceCandidate,
    WorkdaysVacationWorkbookDescriptor,
)

_WORKBOOK_XML_PATH = "xl/workbook.xml"


def parse_workdays_vacation_workbook(
    *,
    descriptor: WorkdaysVacationWorkbookDescriptor,
    payload: bytes,
) -> ParsedWorkdaysVacationWorkbook:
    """Parse one XLSX workbook payload into an explicit workbook contract."""

    try:
        with ZipFile(io.BytesIO(payload)) as archive:
            try:
                workbook_xml = archive.read(_WORKBOOK_XML_PATH)
            except KeyError as error:
                raise ValueError(
                    "Workbook archive is missing the core workbook manifest: "
                    f"{descriptor.origin_label}"
                ) from error
    except BadZipFile as error:
        raise ValueError(
            f"Workdays vacation workbook is not a valid XLSX file: {descriptor.origin_label}"
        ) from error

    try:
        root = ElementTree.fromstring(workbook_xml)
    except ElementTree.ParseError as error:
        raise ValueError(
            f"Workdays vacation workbook XML is invalid: {descriptor.origin_label}"
        ) from error

    sheet_names = tuple(
        name
        for name in (
            sheet_element.attrib.get("name")
            for sheet_element in root.findall(".//{*}sheet")
        )
        if isinstance(name, str) and name
    )
    return ParsedWorkdaysVacationWorkbook(
        descriptor=descriptor,
        sheet_names=sheet_names,
    )


def build_workdays_vacation_source_candidate(
    workbook: ParsedWorkdaysVacationWorkbook,
) -> WorkdaysVacationSourceCandidate:
    """Build the canonical source candidate represented by one workbook."""

    origin_path = workbook.descriptor.origin_path
    return WorkdaysVacationSourceCandidate(
        type="workdays_vacation",
        name=origin_path.stem.replace("_", " ").strip() or origin_path.stem,
        external_id=_build_workbook_external_id(origin_path.as_posix()),
        config_json={
            "origin_path": origin_path.as_posix(),
            "sheet_names": list(workbook.sheet_names),
        },
    )


def build_workdays_vacation_event_candidates(
    workbook: ParsedWorkdaysVacationWorkbook,
) -> tuple[WorkdaysVacationEventCandidate, ...]:
    """Build canonical event candidates for one parsed workbook.

    The workbook row characterization remains intentionally deferred to the
    follow-up parsing task, so the skeleton currently returns no event rows.
    """

    del workbook
    return ()


def _build_workbook_external_id(origin_path: str) -> str:
    digest = hashlib.sha256(origin_path.encode("utf-8")).hexdigest()
    return f"workdays_vacation:{digest}"


__all__ = [
    "build_workdays_vacation_event_candidates",
    "build_workdays_vacation_source_candidate",
    "parse_workdays_vacation_workbook",
]
