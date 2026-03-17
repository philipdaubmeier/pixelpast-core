"""Characterization tests for workdays-vacation ingestion contracts."""

from __future__ import annotations

import io
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

from sqlalchemy import select

from pixelpast.ingestion.workdays_vacation import (
    ParsedWorkdaysVacationDay,
    ParsedWorkdaysVacationWorkbook,
    WorkdaysVacationEventCandidate,
    WorkdaysVacationIngestionResult,
    WorkdaysVacationIngestionService,
    WorkdaysVacationLegendEntry,
    WorkdaysVacationSourceCandidate,
    WorkdaysVacationTransformError,
    WorkdaysVacationWorkbookDescriptor,
    build_workdays_vacation_event_candidates,
    build_workdays_vacation_source_candidate,
    parse_workdays_vacation_workbook,
)
from pixelpast.ingestion.workdays_vacation import contracts as workbook_contracts
from pixelpast.persistence.models import Event, JobRun
from pixelpast.shared.runtime import create_runtime_context, initialize_database
from pixelpast.shared.settings import Settings

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def test_workdays_vacation_public_contract_imports_remain_stable() -> None:
    assert (
        WorkdaysVacationWorkbookDescriptor
        is workbook_contracts.WorkdaysVacationWorkbookDescriptor
    )
    assert (
        ParsedWorkdaysVacationWorkbook
        is workbook_contracts.ParsedWorkdaysVacationWorkbook
    )
    assert ParsedWorkdaysVacationDay is workbook_contracts.ParsedWorkdaysVacationDay
    assert (
        WorkdaysVacationLegendEntry
        is workbook_contracts.WorkdaysVacationLegendEntry
    )
    assert (
        WorkdaysVacationSourceCandidate
        is workbook_contracts.WorkdaysVacationSourceCandidate
    )
    assert (
        WorkdaysVacationEventCandidate
        is workbook_contracts.WorkdaysVacationEventCandidate
    )
    assert (
        WorkdaysVacationTransformError
        is workbook_contracts.WorkdaysVacationTransformError
    )
    assert (
        WorkdaysVacationIngestionResult
        is workbook_contracts.WorkdaysVacationIngestionResult
    )


def test_workdays_vacation_fixture_characterizes_source_and_events() -> None:
    fixture_path = Path("test/assets/workday_vacation_test_fixture.xlsx")

    parsed = parse_workdays_vacation_workbook(
        descriptor=WorkdaysVacationWorkbookDescriptor(path=fixture_path),
        payload=fixture_path.read_bytes(),
    )

    source_candidate = build_workdays_vacation_source_candidate(parsed)
    event_candidates = build_workdays_vacation_event_candidates(parsed)

    assert parsed.descriptor.origin_label == fixture_path.resolve().as_posix()
    assert parsed.sheet_names == ("calendar",)
    assert {entry.code: entry.color_value for entry in parsed.legend_entries} == {
        "O": "#eeeeee",
        "V": "#2f2fab",
        "T": "#66ccff",
    }
    assert len(parsed.day_entries) == 522
    assert len(parsed.skipped_day_warnings) == 207
    assert parsed.skipped_day_warnings[0] == (
        "Skipped workdays vacation day at H5 for 2025-01-04: "
        "unknown legend code 'Sat'."
    )

    assert source_candidate.type == "workdays_vacation"
    assert source_candidate.name == "workday vacation test fixture"
    assert source_candidate.external_id == fixture_path.resolve().as_posix()
    assert source_candidate.config_json == {
        "origin_path": fixture_path.resolve().as_posix(),
        "sheet_names": ["calendar"],
    }

    assert len(event_candidates) == 522
    assert event_candidates[0] == WorkdaysVacationEventCandidate(
        source_external_id=fixture_path.resolve().as_posix(),
        external_event_id="2025-01-01",
        type="workdays_vacation",
        timestamp_start=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
        timestamp_end=datetime(2025, 1, 2, 0, 0, tzinfo=UTC),
        title="V",
        summary=None,
        raw_payload={
            "color_value": "#2f2fab",
            "short_code": "V",
            "legend_description": "Vacation",
            "represented_date": "2025-01-01",
            "worksheet_row": 5,
            "worksheet_column": "E",
        },
        derived_payload=None,
    )
    assert {
        candidate.external_event_id: candidate.title for candidate in event_candidates
    }["2025-03-25"] == "T"
    assert all(candidate.title not in {"Sat", "Sun"} for candidate in event_candidates)


def test_workdays_vacation_parser_reads_first_worksheet_regardless_of_sheet_name(
) -> None:
    fixture_path = Path("test/assets/workday_vacation_test_fixture.xlsx")

    payload = _replace_first_sheet_name(
        fixture_path.read_bytes(),
        replacement_name="renamed-for-test",
    )
    parsed = parse_workdays_vacation_workbook(
        descriptor=WorkdaysVacationWorkbookDescriptor(path=fixture_path),
        payload=payload,
    )

    assert parsed.sheet_names == ("renamed-for-test",)
    assert len(parsed.day_entries) == 522


def test_workdays_vacation_parser_extracts_year_from_anchor_with_suffix_text() -> None:
    fixture_path = Path("test/assets/workday_vacation_test_fixture.xlsx")
    payload = _set_sheet_cell_inline_string(
        fixture_path.read_bytes(),
        cell_reference="B5",
        value="2025 (24 vacation days)",
    )

    parsed = parse_workdays_vacation_workbook(
        descriptor=WorkdaysVacationWorkbookDescriptor(path=fixture_path),
        payload=payload,
    )

    assert len(parsed.day_entries) == 522
    assert parsed.day_entries[0].represented_date.isoformat() == "2025-01-01"


def test_workdays_vacation_parser_rejects_populated_impossible_date() -> None:
    fixture_path = Path("test/assets/workday_vacation_test_fixture.xlsx")
    payload = _set_sheet_cell_shared_string(
        fixture_path.read_bytes(),
        cell_reference="AI6",
        shared_string_index=5,
    )

    try:
        parse_workdays_vacation_workbook(
            descriptor=WorkdaysVacationWorkbookDescriptor(path=fixture_path),
            payload=payload,
        )
    except ValueError as error:
        assert str(error) == (
            "Workdays vacation workbook contains an impossible populated date at "
            "AI6: 2025-02-31"
        )
    else:
        raise AssertionError("Expected impossible populated date to fail.")


def test_workdays_vacation_parser_rejects_invalid_xlsx_payload() -> None:
    descriptor = WorkdaysVacationWorkbookDescriptor(path=Path("invalid.xlsx"))

    try:
        parse_workdays_vacation_workbook(
            descriptor=descriptor,
            payload=b"not-a-zip-workbook",
        )
    except ValueError as error:
        assert str(error) == (
            "Workdays vacation workbook is not a valid XLSX file: "
            f"{descriptor.origin_label}"
        )
    else:
        raise AssertionError("Expected invalid workbook payload to fail.")


def test_workdays_vacation_ingestion_reconciles_changed_new_and_removed_days() -> None:
    runtime = _create_runtime()
    workspace_root = _create_workspace_root()
    fixture_path = Path("test/assets/workday_vacation_test_fixture.xlsx")
    workbook_path = workspace_root / "fixture.xlsx"
    workbook_path.write_bytes(fixture_path.read_bytes())

    try:
        first_result = WorkdaysVacationIngestionService().ingest(
            runtime=runtime,
            root=workbook_path,
        )

        updated_payload = fixture_path.read_bytes()
        updated_payload = _set_sheet_cell_shared_string(
            updated_payload,
            cell_reference="J5",
            shared_string_index=4,
        )
        updated_payload = _set_sheet_cell_shared_string(
            updated_payload,
            cell_reference="H5",
            shared_string_index=5,
        )
        updated_payload = _set_sheet_cell_shared_string(
            updated_payload,
            cell_reference="K5",
            shared_string_index=None,
        )
        workbook_path.write_bytes(updated_payload)

        second_result = WorkdaysVacationIngestionService().ingest(
            runtime=runtime,
            root=workbook_path,
        )

        with runtime.session_factory() as session:
            events = list(
                session.execute(select(Event).order_by(Event.timestamp_start)).scalars()
            )
            job_runs = list(
                session.execute(select(JobRun).order_by(JobRun.id)).scalars()
            )

        titles_by_day = {
            event.raw_payload["external_event_id"]: event.title for event in events
        }

        assert first_result.status == "completed"
        assert first_result.persisted_event_count == 522
        assert second_result.status == "completed"
        assert second_result.persisted_event_count == 522
        assert titles_by_day["2025-01-04"] == "O"
        assert titles_by_day["2025-01-06"] == "V"
        assert "2025-01-07" not in titles_by_day
        assert len(job_runs) == 2
        assert job_runs[1].progress_json == {
            "total": 1,
            "completed": 1,
            "inserted": 1,
            "updated": 1,
            "unchanged": 520,
            "skipped": 206,
            "failed": 0,
            "missing_from_source": 1,
            "persisted_event_count": 522,
        }
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def _create_runtime():
    workspace_root = _create_workspace_root()
    database_path = workspace_root / "pixelpast.db"
    settings = Settings(
        database_url=f"sqlite:///{database_path.as_posix()}",
    )
    runtime = create_runtime_context(settings=settings)
    initialize_database(runtime)
    return runtime


def _create_workspace_root() -> Path:
    workspace_root = Path("var") / "test" / f"workdays-vacation-{uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=True)
    return workspace_root


def _replace_first_sheet_name(payload: bytes, *, replacement_name: str) -> bytes:
    def transform(workbook_xml: bytes) -> bytes:
        root = ElementTree.fromstring(workbook_xml)
        first_sheet = root.find(f".//{{{_MAIN_NS}}}sheet")
        if first_sheet is None:
            raise AssertionError("Expected first worksheet to exist.")
        first_sheet.attrib["name"] = replacement_name
        return ElementTree.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    return _rewrite_zip_member(
        payload,
        member_path="xl/workbook.xml",
        transform=transform,
    )


def _set_sheet_cell_shared_string(
    payload: bytes,
    *,
    cell_reference: str,
    shared_string_index: int | None,
) -> bytes:
    def transform(sheet_xml: bytes) -> bytes:
        root = ElementTree.fromstring(sheet_xml)
        row_number = int(
            "".join(character for character in cell_reference if character.isdigit())
        )
        row = root.find(
            f".//{{{_MAIN_NS}}}sheetData/{{{_MAIN_NS}}}row[@r='{row_number}']"
        )
        if row is None:
            raise AssertionError(f"Expected row {row_number} to exist.")

        cell = None
        for candidate in row.findall(f"{{{_MAIN_NS}}}c"):
            if candidate.attrib.get("r") == cell_reference:
                cell = candidate
                break
        if cell is None:
            raise AssertionError(f"Expected cell {cell_reference} to exist.")

        value_node = cell.find(f"{{{_MAIN_NS}}}v")
        if shared_string_index is None:
            if value_node is not None:
                cell.remove(value_node)
            cell.attrib.pop("t", None)
        else:
            if value_node is None:
                value_node = ElementTree.SubElement(cell, f"{{{_MAIN_NS}}}v")
            cell.attrib["t"] = "s"
            value_node.text = str(shared_string_index)
        return ElementTree.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    return _rewrite_zip_member(
        payload,
        member_path="xl/worksheets/sheet1.xml",
        transform=transform,
    )


def _set_sheet_cell_inline_string(
    payload: bytes,
    *,
    cell_reference: str,
    value: str,
) -> bytes:
    def transform(sheet_xml: bytes) -> bytes:
        root = ElementTree.fromstring(sheet_xml)
        row_number = int(
            "".join(character for character in cell_reference if character.isdigit())
        )
        row = root.find(
            f".//{{{_MAIN_NS}}}sheetData/{{{_MAIN_NS}}}row[@r='{row_number}']"
        )
        if row is None:
            raise AssertionError(f"Expected row {row_number} to exist.")

        cell = None
        for candidate in row.findall(f"{{{_MAIN_NS}}}c"):
            if candidate.attrib.get("r") == cell_reference:
                cell = candidate
                break
        if cell is None:
            raise AssertionError(f"Expected cell {cell_reference} to exist.")

        for child in list(cell):
            cell.remove(child)

        cell.attrib["t"] = "inlineStr"
        inline_string = ElementTree.SubElement(cell, f"{{{_MAIN_NS}}}is")
        text_node = ElementTree.SubElement(inline_string, f"{{{_MAIN_NS}}}t")
        text_node.text = value
        return ElementTree.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    return _rewrite_zip_member(
        payload,
        member_path="xl/worksheets/sheet1.xml",
        transform=transform,
    )


def _rewrite_zip_member(
    payload: bytes,
    *,
    member_path: str,
    transform,
) -> bytes:
    source = io.BytesIO(payload)
    destination = io.BytesIO()
    with zipfile.ZipFile(source, "r") as archive:
        with zipfile.ZipFile(destination, "w") as rewritten:
            for info in archive.infolist():
                content = archive.read(info.filename)
                if info.filename == member_path:
                    content = transform(content)
                rewritten.writestr(info, content)
    return destination.getvalue()
