"""Characterization tests for calendar ingestion contracts and fixture behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pixelpast.ingestion.calendar import (
    CalendarDocumentDescriptor,
    CalendarEventCandidate,
    CalendarIngestionResult,
    CalendarSourceCandidate,
    CalendarTransformError,
    ParsedCalendarDocument,
    ParsedCalendarEvent,
    build_calendar_event_candidates,
    build_calendar_source_candidate,
    parse_calendar_document,
)
from pixelpast.ingestion.calendar import contracts as calendar_contracts


def test_calendar_ingest_public_contract_imports_remain_stable() -> None:
    assert CalendarDocumentDescriptor is calendar_contracts.CalendarDocumentDescriptor
    assert ParsedCalendarDocument is calendar_contracts.ParsedCalendarDocument
    assert ParsedCalendarEvent is calendar_contracts.ParsedCalendarEvent
    assert CalendarSourceCandidate is calendar_contracts.CalendarSourceCandidate
    assert CalendarEventCandidate is calendar_contracts.CalendarEventCandidate
    assert CalendarTransformError is calendar_contracts.CalendarTransformError
    assert CalendarIngestionResult is calendar_contracts.CalendarIngestionResult


def test_outlook_fixture_characterizes_calendar_headers_and_html_description() -> None:
    fixture_path = Path("test/assets/outlook_cal_export_test_fixture.ics")

    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=fixture_path),
        text=fixture_path.read_text(encoding="utf-8"),
    )

    assert parsed.calendar_name_header == "X-WR-CALNAME"
    assert parsed.calendar_name == "MyCalendar"
    assert parsed.calendar_external_id_header == "X-WR-RELCALID"
    assert (
        parsed.calendar_external_id
        == "{0000002E-4C28-07C7-8A98-F77FE2214668}"
    )
    assert parsed.timezone_ids == (
        "(UTC+01:00) Amsterdam, Berlin, B",
        "Greenwich Standard Time",
    )

    assert len(parsed.events) == 1
    event = parsed.events[0]
    assert event.uid == (
        "040000009700E05574E5B7101A82E0080000000040602848012EEF01043000012077000"
        "0100000003FEC8C5443BE644DA03A2F440F6B085C"
    )
    assert event.summary == "My Appointment"
    assert event.alt_description_format == "text/html"

    candidates = build_calendar_event_candidates(parsed)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.timestamp_start == datetime(2020, 6, 15, 7, 0, tzinfo=UTC)
    assert candidate.timestamp_end == datetime(2020, 6, 15, 8, 0, tzinfo=UTC)
    assert candidate.title == "My Appointment"
    assert candidate.summary == "...some long html file content..."


def test_calendar_document_contract_models_one_source_candidate_and_many_events() -> None:
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=Path("calendar.ics")),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "X-WR-CALNAME:Trips\n"
            "X-WR-RELCALID:cal-123\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART:20240102T090000Z\n"
            "SUMMARY:Departure\n"
            "END:VEVENT\n"
            "BEGIN:VEVENT\n"
            "UID:event-2\n"
            "DTSTART:20240103T180000Z\n"
            "SUMMARY:Arrival\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    source_candidate = build_calendar_source_candidate(parsed)
    event_candidates = build_calendar_event_candidates(parsed)

    assert source_candidate.type == "calendar"
    assert source_candidate.name == "Trips"
    assert source_candidate.external_id == "cal-123"
    assert source_candidate.config_json == {
        "origin_path": (Path("calendar.ics").resolve().as_posix()),
        "archive_member_path": None,
        "calendar_name_header": "X-WR-CALNAME",
        "calendar_external_id_header": "X-WR-RELCALID",
        "timezone_ids": [],
    }
    assert len(event_candidates) == 2
    assert [candidate.external_event_id for candidate in event_candidates] == [
        "event-1",
        "event-2",
    ]


def test_calendar_source_candidate_uses_archive_origin_without_fake_extraction_path() -> None:
    archive_path = Path("calendar-export.zip")
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(
            path=archive_path,
            archive_member_path="nested/work.ics",
        ),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "X-WR-CALNAME:Work\n"
            "X-WR-RELCALID:work-cal\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART:20240102T090000Z\n"
            "SUMMARY:Standup\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    source_candidate = build_calendar_source_candidate(parsed)

    assert source_candidate.config_json == {
        "origin_path": archive_path.resolve().as_posix(),
        "archive_member_path": "nested/work.ics",
        "calendar_name_header": "X-WR-CALNAME",
        "calendar_external_id_header": "X-WR-RELCALID",
        "timezone_ids": [],
    }


def test_calendar_source_candidate_fails_without_external_id_header() -> None:
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=Path("calendar.ics")),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "X-WR-CALNAME:Trips\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART:20240102T090000Z\n"
            "SUMMARY:Departure\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    try:
        build_calendar_source_candidate(parsed)
    except ValueError as error:
        assert str(error) == (
            "Calendar document "
            f"'{Path('calendar.ics').resolve().as_posix()}' is missing a required "
            "external id header (X-WR-RELCALID, X-WR-RECALID)."
        )
    else:
        raise AssertionError("Expected missing calendar external id to fail.")


def test_calendar_event_title_truncation_keeps_220_characters_then_ellipsis() -> None:
    long_summary = "A" * 221
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=Path("calendar.ics")),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART:20240102T090000Z\n"
            f"SUMMARY:{long_summary}\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    candidate = build_calendar_event_candidates(parsed)[0]

    assert candidate.title == f'{"A" * 220}...'


def test_calendar_plaintext_alt_description_is_stored_as_is() -> None:
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=Path("calendar.ics")),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART:20240102T090000Z\n"
            "SUMMARY:Plain text description\n"
            "X-ALT-DESC:Line one\\nLine two\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    candidate = build_calendar_event_candidates(parsed)[0]

    assert candidate.summary == "Line one\nLine two"


def test_calendar_html_alt_description_removes_markup_and_ignores_images() -> None:
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=Path("calendar.ics")),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART:20240102T090000Z\n"
            "SUMMARY:HTML description\n"
            "X-ALT-DESC;FMTTYPE=text/html:<div>Hello <img src=\"x\">World &amp; beyond</div>\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    candidate = build_calendar_event_candidates(parsed)[0]

    assert candidate.summary == "Hello World & beyond"


def test_calendar_parser_keeps_standard_tzid_datetimes_timezone_aware() -> None:
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=Path("calendar.ics")),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART;TZID=Europe/Berlin:20240102T091500\n"
            "DTEND;TZID=Europe/Berlin:20240102T104500\n"
            "SUMMARY:Berlin example\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    event = parsed.events[0]
    candidate = build_calendar_event_candidates(parsed)[0]

    assert event.starts_at.tzinfo is not None
    assert event.ends_at is not None
    assert event.ends_at.tzinfo is not None
    assert candidate.timestamp_start == datetime(2024, 1, 2, 8, 15, tzinfo=UTC)
    assert candidate.timestamp_end == datetime(2024, 1, 2, 9, 45, tzinfo=UTC)


def test_calendar_timezones_are_normalized_to_utc_before_persistence() -> None:
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=Path("calendar.ics")),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "BEGIN:VTIMEZONE\n"
            "TZID:America/New_York\n"
            "BEGIN:STANDARD\n"
            "DTSTART:16011101T020000\n"
            "RRULE:FREQ=YEARLY;BYDAY=1SU;BYMONTH=11\n"
            "TZOFFSETFROM:-0400\n"
            "TZOFFSETTO:-0500\n"
            "END:STANDARD\n"
            "BEGIN:DAYLIGHT\n"
            "DTSTART:16010308T020000\n"
            "RRULE:FREQ=YEARLY;BYDAY=2SU;BYMONTH=3\n"
            "TZOFFSETFROM:-0500\n"
            "TZOFFSETTO:-0400\n"
            "END:DAYLIGHT\n"
            "END:VTIMEZONE\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART;TZID=America/New_York:20240102T091500\n"
            "DTEND;TZID=America/New_York:20240102T104500\n"
            "SUMMARY:Offset example\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    candidate = build_calendar_event_candidates(parsed)[0]

    assert candidate.timestamp_start == datetime(2024, 1, 2, 14, 15, tzinfo=UTC)
    assert candidate.timestamp_end == datetime(2024, 1, 2, 15, 45, tzinfo=UTC)


def test_calendar_date_only_events_are_normalized_to_utc_midnight() -> None:
    parsed = parse_calendar_document(
        descriptor=CalendarDocumentDescriptor(path=Path("calendar.ics")),
        text=(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "X-WR-RELCALID:cal-123\n"
            "BEGIN:VEVENT\n"
            "UID:event-1\n"
            "DTSTART;VALUE=DATE:20240102\n"
            "DTEND;VALUE=DATE:20240103\n"
            "SUMMARY:All day\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        ),
    )

    candidate = build_calendar_event_candidates(parsed)[0]

    assert candidate.timestamp_start == datetime(2024, 1, 2, 0, 0, tzinfo=UTC)
    assert candidate.timestamp_end == datetime(2024, 1, 3, 0, 0, tzinfo=UTC)
