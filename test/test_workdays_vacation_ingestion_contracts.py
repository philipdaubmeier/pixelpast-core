"""Characterization tests for workdays-vacation ingestion contracts."""

from __future__ import annotations

from pathlib import Path

from pixelpast.ingestion.workdays_vacation import (
    ParsedWorkdaysVacationWorkbook,
    WorkdaysVacationEventCandidate,
    WorkdaysVacationIngestionResult,
    WorkdaysVacationSourceCandidate,
    WorkdaysVacationTransformError,
    WorkdaysVacationWorkbookDescriptor,
    build_workdays_vacation_event_candidates,
    build_workdays_vacation_source_candidate,
    parse_workdays_vacation_workbook,
)
from pixelpast.ingestion.workdays_vacation import contracts as workbook_contracts


def test_workdays_vacation_public_contract_imports_remain_stable() -> None:
    assert (
        WorkdaysVacationWorkbookDescriptor
        is workbook_contracts.WorkdaysVacationWorkbookDescriptor
    )
    assert (
        ParsedWorkdaysVacationWorkbook
        is workbook_contracts.ParsedWorkdaysVacationWorkbook
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


def test_workdays_vacation_fixture_characterizes_workbook_level_source_candidate() -> None:
    fixture_path = Path("test/assets/workday_vacation_test_fixture.xlsx")

    parsed = parse_workdays_vacation_workbook(
        descriptor=WorkdaysVacationWorkbookDescriptor(path=fixture_path),
        payload=fixture_path.read_bytes(),
    )

    assert parsed.descriptor.origin_label == fixture_path.resolve().as_posix()
    assert parsed.sheet_names

    source_candidate = build_workdays_vacation_source_candidate(parsed)
    event_candidates = build_workdays_vacation_event_candidates(parsed)

    assert source_candidate.type == "workdays_vacation"
    assert source_candidate.name == "workday vacation test fixture"
    assert source_candidate.external_id is not None
    assert source_candidate.external_id.startswith("workdays_vacation:")
    assert source_candidate.config_json == {
        "origin_path": fixture_path.resolve().as_posix(),
        "sheet_names": list(parsed.sheet_names),
    }
    assert event_candidates == ()


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
