"""Calendar document parsing and canonical transformation helpers."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Iterable

from pixelpast.ingestion.calendar.contracts import (
    CalendarDocumentDescriptor,
    CalendarEventCandidate,
    CalendarParsedProperty,
    CalendarSourceCandidate,
    ParsedCalendarDocument,
    ParsedCalendarEvent,
)

_TITLE_MAX_LENGTH = 220
_CALENDAR_NAME_HEADERS = ("X-WR-CALNAME",)
_CALENDAR_EXTERNAL_ID_HEADERS = ("X-WR-RELCALID", "X-WR-RECALID")


def parse_calendar_document(
    *,
    descriptor: CalendarDocumentDescriptor,
    text: str,
) -> ParsedCalendarDocument:
    """Parse one VCALENDAR text payload into an explicit document contract."""

    lines = _unfold_ical_lines(text)
    calendar_properties: list[CalendarParsedProperty] = []
    timezone_ids: list[str] = []
    events: list[ParsedCalendarEvent] = []

    active_component: str | None = None
    active_event_properties: list[CalendarParsedProperty] = []

    for line in lines:
        if not line:
            continue
        if line == "BEGIN:VEVENT":
            active_component = "VEVENT"
            active_event_properties = []
            continue
        if line == "END:VEVENT":
            events.append(_build_parsed_event(active_event_properties))
            active_component = None
            active_event_properties = []
            continue
        if line == "BEGIN:VTIMEZONE":
            active_component = "VTIMEZONE"
            continue
        if line == "END:VTIMEZONE":
            active_component = None
            continue
        if line.startswith("BEGIN:") or line.startswith("END:"):
            continue

        parsed_property = _parse_property_line(line)
        if active_component == "VEVENT":
            active_event_properties.append(parsed_property)
            continue
        if active_component == "VTIMEZONE":
            if parsed_property.name == "TZID":
                timezone_ids.append(parsed_property.value)
            continue
        calendar_properties.append(parsed_property)

    name_property = _find_first_property(calendar_properties, _CALENDAR_NAME_HEADERS)
    external_id_property = _find_first_property(
        calendar_properties,
        _CALENDAR_EXTERNAL_ID_HEADERS,
    )

    return ParsedCalendarDocument(
        descriptor=descriptor,
        calendar_name_header=name_property.name if name_property is not None else None,
        calendar_name=name_property.value if name_property is not None else None,
        calendar_external_id_header=(
            external_id_property.name if external_id_property is not None else None
        ),
        calendar_external_id=(
            external_id_property.value if external_id_property is not None else None
        ),
        timezone_ids=tuple(timezone_ids),
        properties=tuple(calendar_properties),
        events=tuple(events),
    )


def build_calendar_source_candidate(
    document: ParsedCalendarDocument,
) -> CalendarSourceCandidate:
    """Build the canonical source candidate represented by one calendar document."""

    return CalendarSourceCandidate(
        type="calendar",
        name=document.calendar_name,
        external_id=document.calendar_external_id,
        config_json={
            "document_path": document.descriptor.path.as_posix(),
            "archive_member_path": document.descriptor.archive_member_path,
            "calendar_name_header": document.calendar_name_header,
            "calendar_external_id_header": document.calendar_external_id_header,
            "timezone_ids": list(document.timezone_ids),
        },
    )


def build_calendar_event_candidates(
    document: ParsedCalendarDocument,
) -> tuple[CalendarEventCandidate, ...]:
    """Build canonical calendar event candidates for one parsed document."""

    return tuple(
        CalendarEventCandidate(
            source_external_id=document.calendar_external_id,
            external_event_id=event.uid,
            type="calendar",
            timestamp_start=event.starts_at.astimezone(UTC),
            timestamp_end=(
                event.ends_at.astimezone(UTC) if event.ends_at is not None else None
            ),
            title=_normalize_title(event.summary),
            summary=_normalize_alt_description(
                value=event.alt_description,
                fmt_type=event.alt_description_format,
            ),
            raw_payload=_build_raw_event_payload(event),
            derived_payload=None,
        )
        for event in document.events
    )


def _build_parsed_event(
    properties: Iterable[CalendarParsedProperty],
) -> ParsedCalendarEvent:
    event_properties = tuple(properties)
    uid_property = _find_first_property(event_properties, ("UID",))
    dtstart_property = _find_first_property(event_properties, ("DTSTART",))
    if dtstart_property is None:
        raise ValueError("VEVENT is missing DTSTART.")
    dtend_property = _find_first_property(event_properties, ("DTEND",))
    summary_property = _find_first_property(event_properties, ("SUMMARY",))
    alt_description_property = _find_first_property(event_properties, ("X-ALT-DESC",))

    return ParsedCalendarEvent(
        uid=uid_property.value if uid_property is not None else None,
        starts_at=_parse_ical_datetime(dtstart_property),
        ends_at=(
            _parse_ical_datetime(dtend_property) if dtend_property is not None else None
        ),
        summary=summary_property.value if summary_property is not None else None,
        alt_description=(
            alt_description_property.value
            if alt_description_property is not None
            else None
        ),
        alt_description_format=(
            alt_description_property.get_parameter("FMTTYPE")
            if alt_description_property is not None
            else None
        ),
        properties=event_properties,
    )


def _find_first_property(
    properties: Iterable[CalendarParsedProperty],
    names: tuple[str, ...],
) -> CalendarParsedProperty | None:
    normalized_names = {name.upper() for name in names}
    for property_value in properties:
        if property_value.name.upper() in normalized_names:
            return property_value
    return None


def _parse_property_line(line: str) -> CalendarParsedProperty:
    before_value, value = _split_property_line(line)
    parts = before_value.split(";")
    name = parts[0].upper()
    parameters: list[tuple[str, str]] = []
    for parameter in parts[1:]:
        parameter_name, parameter_value = parameter.split("=", maxsplit=1)
        parameters.append(
            (
                parameter_name.upper(),
                _strip_wrapping_quotes(_unescape_ical_text(parameter_value)),
            )
        )
    return CalendarParsedProperty(
        name=name,
        value=_unescape_ical_text(value),
        parameters=tuple(parameters),
    )


def _split_property_line(line: str) -> tuple[str, str]:
    in_quotes = False
    for index, character in enumerate(line):
        if character == '"':
            in_quotes = not in_quotes
            continue
        if character == ":" and not in_quotes:
            return line[:index], line[index + 1 :]
    raise ValueError(f"Invalid iCalendar property line '{line}'.")


def _parse_ical_datetime(property_value: CalendarParsedProperty) -> datetime:
    value = property_value.value
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)

    parsed_datetime = datetime.strptime(value, "%Y%m%dT%H%M%S")
    tzid = property_value.get_parameter("TZID")
    if tzid is None:
        return parsed_datetime.replace(tzinfo=UTC)

    return parsed_datetime.replace(tzinfo=_timezone_from_tzid(tzid))


def _timezone_from_tzid(tzid: str) -> timezone:
    normalized_tzid = tzid.strip()
    if normalized_tzid.upper() == "UTC":
        return timezone.utc

    if normalized_tzid.startswith("(UTC") and ")" in normalized_tzid:
        offset_token = normalized_tzid[4 : normalized_tzid.index(")")]
        return timezone(_parse_utc_offset(offset_token))

    raise ValueError(f"Unsupported TZID value '{tzid}'.")


def _parse_utc_offset(value: str) -> timedelta:
    sign = 1 if value.startswith("+") else -1
    hours = int(value[1:3])
    minutes = int(value[4:6])
    return timedelta(hours=sign * hours, minutes=sign * minutes)


def _normalize_title(summary: str | None) -> str | None:
    if summary is None:
        return None
    if len(summary) <= _TITLE_MAX_LENGTH:
        return summary
    return f"{summary[:_TITLE_MAX_LENGTH]}..."


def _normalize_alt_description(*, value: str | None, fmt_type: str | None) -> str | None:
    if value is None:
        return None
    if fmt_type is None or fmt_type.lower() == "text/plain":
        return value
    if fmt_type.lower() == "text/html":
        return _html_to_plaintext(value)
    return value


def _build_raw_event_payload(event: ParsedCalendarEvent) -> dict[str, object]:
    return {
        "uid": event.uid,
        "summary": event.summary,
        "alt_description": event.alt_description,
        "alt_description_format": event.alt_description_format,
        "properties": [asdict(property_value) for property_value in event.properties],
    }


def _unfold_ical_lines(text: str) -> list[str]:
    unfolded_lines: list[str] = []
    for raw_line in text.splitlines():
        if raw_line.startswith((" ", "\t")) and unfolded_lines:
            unfolded_lines[-1] += raw_line[1:]
            continue
        unfolded_lines.append(raw_line)
    return unfolded_lines


def _unescape_ical_text(value: str) -> str:
    return (
        value.replace("\\\\", "\\")
        .replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
    )


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


class _CalendarHtmlTextExtractor(HTMLParser):
    """Extract human-readable text while ignoring images and markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        del attrs
        if tag in {"br", "div", "p", "li"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"div", "p", "li"}:
            self._parts.append("\n")

    def get_text(self) -> str:
        text = unescape("".join(self._parts))
        lines = [" ".join(line.split()) for line in text.splitlines()]
        return "\n".join(line for line in lines if line)


def _html_to_plaintext(value: str) -> str:
    parser = _CalendarHtmlTextExtractor()
    parser.feed(value)
    parser.close()
    return parser.get_text()


__all__ = [
    "build_calendar_event_candidates",
    "build_calendar_source_candidate",
    "parse_calendar_document",
]
