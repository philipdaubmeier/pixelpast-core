"""Workbook parsing and canonical transformation helpers."""

from __future__ import annotations

import io
import re
from datetime import UTC, date, datetime, time, timedelta
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pixelpast.ingestion.workdays_vacation.contracts import (
    ParsedWorkdaysVacationDay,
    ParsedWorkdaysVacationWorkbook,
    WorkdaysVacationEventCandidate,
    WorkdaysVacationLegendEntry,
    WorkdaysVacationSourceCandidate,
    WorkdaysVacationWorkbookDescriptor,
)

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _column_index(column_letters: str) -> int:
    value = 0
    for character in column_letters:
        value = (value * 26) + (ord(character.upper()) - 64)
    return value


def _column_letters(column_index: int) -> str:
    letters: list[str] = []
    remaining = column_index
    while remaining > 0:
        remaining, remainder = divmod(remaining - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))

_WORKBOOK_XML_PATH = "xl/workbook.xml"
_WORKBOOK_RELS_XML_PATH = "xl/_rels/workbook.xml.rels"

_TITLE_ROW_END = 3
_DAY_HEADER_ROW = 4
_DATA_ROW_START = 5
_YEAR_ANCHOR_COLUMN = _column_index("B")
_MONTH_ANCHOR_COLUMN = _column_index("C")
_MATRIX_START_COLUMN = _column_index("E")
_MATRIX_END_COLUMN = _column_index("AI")
_LEGEND_CODE_COLUMN = _column_index("AK")
_LEGEND_DESCRIPTION_COLUMN = _column_index("AL")
_LEGEND_COLOR_COLUMN = _column_index("AW")
_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
_EXCEL_EPOCH = date(1899, 12, 30)


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
                workbook_rels_xml = archive.read(_WORKBOOK_RELS_XML_PATH)
            except KeyError as error:
                raise ValueError(
                    "Workbook archive is missing the core workbook manifest: "
                    f"{descriptor.origin_label}"
                ) from error

            sheet_names, first_sheet_path = _parse_workbook_manifest(
                descriptor=descriptor,
                workbook_xml=workbook_xml,
                workbook_rels_xml=workbook_rels_xml,
            )
            shared_strings = _load_shared_strings(archive)
            worksheet_xml = archive.read(first_sheet_path)
    except BadZipFile as error:
        raise ValueError(
            "Workdays vacation workbook is not a valid XLSX file: "
            f"{descriptor.origin_label}"
        ) from error

    worksheet_cells = _parse_worksheet_cells(
        descriptor=descriptor,
        worksheet_xml=worksheet_xml,
        shared_strings=shared_strings,
    )
    day_headers = _parse_day_headers(
        descriptor=descriptor,
        worksheet_cells=worksheet_cells,
    )
    legend_entries = _parse_legend_entries(
        descriptor=descriptor,
        worksheet_cells=worksheet_cells,
    )
    day_entries, skipped_day_warnings = _parse_day_entries(
        descriptor=descriptor,
        worksheet_cells=worksheet_cells,
        day_headers=day_headers,
        legend_entries=legend_entries,
    )

    return ParsedWorkdaysVacationWorkbook(
        descriptor=descriptor,
        sheet_names=sheet_names,
        legend_entries=tuple(legend_entries.values()),
        day_entries=day_entries,
        skipped_day_warnings=skipped_day_warnings,
    )


def build_workdays_vacation_source_candidate(
    workbook: ParsedWorkdaysVacationWorkbook,
) -> WorkdaysVacationSourceCandidate:
    """Build the canonical source candidate represented by one workbook."""

    origin_path = workbook.descriptor.origin_path
    return WorkdaysVacationSourceCandidate(
        type="workdays_vacation",
        name=origin_path.stem.replace("_", " ").strip() or origin_path.stem,
        external_id=origin_path.as_posix(),
        config_json={
            "origin_path": origin_path.as_posix(),
            "sheet_names": list(workbook.sheet_names),
        },
    )


def build_workdays_vacation_event_candidates(
    workbook: ParsedWorkdaysVacationWorkbook,
) -> tuple[WorkdaysVacationEventCandidate, ...]:
    """Build canonical event candidates for one parsed workbook."""

    source_external_id = workbook.descriptor.origin_path.as_posix()
    return tuple(
        WorkdaysVacationEventCandidate(
            source_external_id=source_external_id,
            external_event_id=entry.represented_date.isoformat(),
            type="workdays_vacation",
            timestamp_start=datetime.combine(
                entry.represented_date,
                time.min,
                tzinfo=UTC,
            ),
            timestamp_end=datetime.combine(
                entry.represented_date + timedelta(days=1),
                time.min,
                tzinfo=UTC,
            ),
            title=entry.short_code,
            summary=None,
            raw_payload={
                "color_value": entry.color_value,
                "short_code": entry.short_code,
                "legend_description": entry.legend_description,
                "represented_date": entry.represented_date.isoformat(),
                "worksheet_row": entry.worksheet_row,
                "worksheet_column": entry.worksheet_column,
            },
            derived_payload=None,
        )
        for entry in workbook.day_entries
    )


def _parse_workbook_manifest(
    *,
    descriptor: WorkdaysVacationWorkbookDescriptor,
    workbook_xml: bytes,
    workbook_rels_xml: bytes,
) -> tuple[tuple[str, ...], str]:
    workbook_root = _parse_xml(
        payload=workbook_xml,
        error_message=(
            f"Workdays vacation workbook XML is invalid: {descriptor.origin_label}"
        ),
    )
    rels_root = _parse_xml(
        payload=workbook_rels_xml,
        error_message=(
            "Workdays vacation workbook relationships XML is invalid: "
            f"{descriptor.origin_label}"
        ),
    )

    sheet_elements = workbook_root.findall(f".//{{{_MAIN_NS}}}sheet")
    if not sheet_elements:
        raise ValueError(
            "Workdays vacation workbook does not contain any worksheets: "
            f"{descriptor.origin_label}"
        )

    sheet_names = tuple(
        sheet.attrib.get("name")
        for sheet in sheet_elements
        if isinstance(sheet.attrib.get("name"), str) and sheet.attrib.get("name")
    )
    if not sheet_names:
        raise ValueError(
            "Workdays vacation workbook is missing a usable first worksheet name: "
            f"{descriptor.origin_label}"
        )

    relationship_targets = {
        relationship.attrib.get("Id"): relationship.attrib.get("Target")
        for relationship in rels_root.findall(f".//{{{_PACKAGE_REL_NS}}}Relationship")
    }
    first_sheet = sheet_elements[0]
    relationship_id = first_sheet.attrib.get(f"{{{_REL_NS}}}id")
    target = relationship_targets.get(relationship_id)
    if not isinstance(target, str) or not target:
        raise ValueError(
            "Workdays vacation workbook is missing the first worksheet relationship: "
            f"{descriptor.origin_label}"
        )

    sheet_path = PurePosixPath("xl") / PurePosixPath(target)
    return sheet_names, sheet_path.as_posix()


def _load_shared_strings(archive: ZipFile) -> tuple[str, ...]:
    try:
        shared_strings_xml = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return ()

    root = _parse_xml(
        payload=shared_strings_xml,
        error_message="Workdays vacation workbook shared strings XML is invalid.",
    )
    strings: list[str] = []
    for item in root.findall(f".//{{{_MAIN_NS}}}si"):
        text_parts = [
            text_node.text or ""
            for text_node in item.findall(f".//{{{_MAIN_NS}}}t")
        ]
        strings.append("".join(text_parts))
    return tuple(strings)


def _parse_worksheet_cells(
    *,
    descriptor: WorkdaysVacationWorkbookDescriptor,
    worksheet_xml: bytes,
    shared_strings: tuple[str, ...],
) -> dict[int, dict[int, object]]:
    root = _parse_xml(
        payload=worksheet_xml,
        error_message=(
            f"Workdays vacation worksheet XML is invalid: {descriptor.origin_label}"
        ),
    )

    worksheet_cells: dict[int, dict[int, object]] = {}
    for row_element in root.findall(f".//{{{_MAIN_NS}}}sheetData/{{{_MAIN_NS}}}row"):
        row_index = int(row_element.attrib["r"])
        row_cells: dict[int, object] = {}
        for cell_element in row_element.findall(f"{{{_MAIN_NS}}}c"):
            cell_reference = cell_element.attrib.get("r")
            if not isinstance(cell_reference, str):
                continue
            column_letters = "".join(
                character for character in cell_reference if character.isalpha()
            )
            if not column_letters:
                continue
            value = _parse_cell_value(
                cell_element=cell_element,
                shared_strings=shared_strings,
            )
            if value is None:
                continue
            row_cells[_column_index(column_letters)] = value
        if row_cells:
            worksheet_cells[row_index] = row_cells
    return worksheet_cells


def _parse_day_headers(
    *,
    descriptor: WorkdaysVacationWorkbookDescriptor,
    worksheet_cells: dict[int, dict[int, object]],
) -> dict[int, int]:
    header_row = worksheet_cells.get(_DAY_HEADER_ROW, {})
    day_headers: dict[int, int] = {}
    for column_index in range(_MATRIX_START_COLUMN, _MATRIX_END_COLUMN + 1):
        header_value = header_row.get(column_index)
        day_number = _coerce_required_int(
            value=header_value,
            error_message=(
                "Workdays vacation workbook day header is invalid at "
                f"{_column_letters(column_index)}{_DAY_HEADER_ROW}: "
                f"{descriptor.origin_label}"
            ),
        )
        if day_number != (column_index - _MATRIX_START_COLUMN + 1):
            raise ValueError(
                "Workdays vacation workbook day header is misaligned at "
                f"{_column_letters(column_index)}{_DAY_HEADER_ROW}: expected "
                f"{column_index - _MATRIX_START_COLUMN + 1}, got {day_number}"
            )
        day_headers[column_index] = day_number
    return day_headers


def _parse_legend_entries(
    *,
    descriptor: WorkdaysVacationWorkbookDescriptor,
    worksheet_cells: dict[int, dict[int, object]],
) -> dict[str, WorkdaysVacationLegendEntry]:
    legend_entries: dict[str, WorkdaysVacationLegendEntry] = {}
    for row_index in sorted(row for row in worksheet_cells if row >= _DATA_ROW_START):
        row = worksheet_cells[row_index]
        code = _trimmed_string(row.get(_LEGEND_CODE_COLUMN))
        if code is None:
            continue
        color_value = _trimmed_string(row.get(_LEGEND_COLOR_COLUMN))
        if color_value is None or not _HEX_COLOR_PATTERN.fullmatch(color_value):
            raise ValueError(
                "Workdays vacation legend color is invalid at "
                f"{_column_letters(_LEGEND_COLOR_COLUMN)}{row_index}: "
                f"{descriptor.origin_label}"
            )
        legend_entries[code] = WorkdaysVacationLegendEntry(
            code=code,
            description=_trimmed_string(row.get(_LEGEND_DESCRIPTION_COLUMN)),
            color_value=color_value,
        )
    return legend_entries


def _parse_day_entries(
    *,
    descriptor: WorkdaysVacationWorkbookDescriptor,
    worksheet_cells: dict[int, dict[int, object]],
    day_headers: dict[int, int],
    legend_entries: dict[str, WorkdaysVacationLegendEntry],
) -> tuple[tuple[ParsedWorkdaysVacationDay, ...], tuple[str, ...]]:
    day_entries: list[ParsedWorkdaysVacationDay] = []
    skipped_day_warnings: list[str] = []
    active_year: int | None = None

    for row_index in sorted(row for row in worksheet_cells if row >= _DATA_ROW_START):
        row = worksheet_cells[row_index]
        year_anchor_value = row.get(_YEAR_ANCHOR_COLUMN)
        if year_anchor_value is not None:
            active_year = _coerce_required_int(
                value=year_anchor_value,
                error_message=(
                    "Workdays vacation year anchor is invalid at "
                    f"{_column_letters(_YEAR_ANCHOR_COLUMN)}{row_index}: "
                    f"{descriptor.origin_label}"
                ),
            )

        populated_matrix_columns = [
            column_index
            for column_index in range(_MATRIX_START_COLUMN, _MATRIX_END_COLUMN + 1)
            if _trimmed_string(row.get(column_index)) is not None
        ]
        month_anchor_value = row.get(_MONTH_ANCHOR_COLUMN)
        if month_anchor_value is None:
            if populated_matrix_columns:
                raise ValueError(
                    "Workdays vacation month anchor is missing for populated row "
                    f"{row_index}: {descriptor.origin_label}"
                )
            continue

        if active_year is None:
            raise ValueError(
                "Workdays vacation row is missing an active year anchor before "
                f"row {row_index}: {descriptor.origin_label}"
            )

        month_anchor = _coerce_excel_date(
            value=month_anchor_value,
            error_message=(
                "Workdays vacation month anchor is invalid at "
                f"{_column_letters(_MONTH_ANCHOR_COLUMN)}{row_index}: "
                f"{descriptor.origin_label}"
            ),
        )
        if month_anchor.day != 1:
            raise ValueError(
                "Workdays vacation month anchor must represent the first day of the "
                f"month at {_column_letters(_MONTH_ANCHOR_COLUMN)}{row_index}: "
                f"{descriptor.origin_label}"
            )
        if month_anchor.year != active_year:
            raise ValueError(
                "Workdays vacation year anchor does not match month anchor at "
                f"{_column_letters(_MONTH_ANCHOR_COLUMN)}{row_index}: expected "
                f"{active_year}, got {month_anchor.year}"
            )

        for column_index in populated_matrix_columns:
            short_code = _trimmed_string(row.get(column_index))
            if short_code is None:
                continue
            day_number = day_headers[column_index]
            try:
                represented_date = date(active_year, month_anchor.month, day_number)
            except ValueError as error:
                raise ValueError(
                    "Workdays vacation workbook contains an impossible populated "
                    f"date at {_column_letters(column_index)}{row_index}: "
                    f"{active_year:04d}-{month_anchor.month:02d}-{day_number:02d}"
                ) from error

            legend_entry = legend_entries.get(short_code)
            if legend_entry is None:
                skipped_day_warnings.append(
                    "Skipped workdays vacation day at "
                    f"{_column_letters(column_index)}{row_index} for "
                    f"{represented_date.isoformat()}: unknown legend code "
                    f"'{short_code}'."
                )
                continue

            day_entries.append(
                ParsedWorkdaysVacationDay(
                    represented_date=represented_date,
                    short_code=short_code,
                    color_value=legend_entry.color_value,
                    legend_description=legend_entry.description,
                    worksheet_row=row_index,
                    worksheet_column=_column_letters(column_index),
                )
            )

    return tuple(day_entries), tuple(skipped_day_warnings)


def _parse_cell_value(
    *,
    cell_element: ElementTree.Element,
    shared_strings: tuple[str, ...],
) -> object | None:
    value_node = cell_element.find(f"{{{_MAIN_NS}}}v")
    cell_type = cell_element.attrib.get("t")

    if cell_type == "inlineStr":
        text_parts = [
            text_node.text or ""
            for text_node in cell_element.findall(f".//{{{_MAIN_NS}}}t")
        ]
        value = "".join(text_parts)
        return value if value != "" else None

    if value_node is None or value_node.text is None:
        return None

    raw_value = value_node.text
    if cell_type == "s":
        return shared_strings[int(raw_value)]
    if cell_type in {"str", "e"}:
        return raw_value

    try:
        numeric_value = float(raw_value)
    except ValueError:
        return raw_value
    if numeric_value.is_integer():
        return int(numeric_value)
    return numeric_value


def _coerce_required_int(*, value: object | None, error_message: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    trimmed = _trimmed_string(value)
    if trimmed is not None:
        try:
            return int(trimmed)
        except ValueError:
            pass
    raise ValueError(error_message)


def _coerce_excel_date(*, value: object, error_message: str) -> date:
    if isinstance(value, int):
        return _EXCEL_EPOCH + timedelta(days=value)
    if isinstance(value, float) and value.is_integer():
        return _EXCEL_EPOCH + timedelta(days=int(value))
    raise ValueError(error_message)


def _trimmed_string(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_xml(*, payload: bytes, error_message: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        raise ValueError(error_message) from error


__all__ = [
    "build_workdays_vacation_event_candidates",
    "build_workdays_vacation_source_candidate",
    "parse_workdays_vacation_workbook",
]
