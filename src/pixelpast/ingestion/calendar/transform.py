"""Calendar document parsing and canonical transformation helpers."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, date, datetime, time
from html import unescape
from html.parser import HTMLParser
from typing import Any

from icalendar import Calendar
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

    calendar = Calendar.from_ical(text)
    timezone_ids = tuple(
        str(component.get("TZID"))
        for component in calendar.walk("VTIMEZONE")
        if component.get("TZID") is not None
    )
    calendar_properties = tuple(
        _build_parsed_property(name=name, value=value)
        for name, value in calendar.property_items(recursive=False, sorted=False)
        if name not in {"BEGIN", "END"}
    )
    events = tuple(
        _build_parsed_event(component=event) for event in calendar.walk("VEVENT")
    )

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
        timezone_ids=timezone_ids,
        properties=calendar_properties,
        events=events,
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
    *,
    component,
) -> ParsedCalendarEvent:
    event_properties = tuple(
        _build_parsed_property(name=name, value=value)
        for name, value in component.property_items(recursive=False, sorted=False)
        if name not in {"BEGIN", "END"}
    )
    uid_property = _find_first_property(event_properties, ("UID",))
    dtstart_property = _find_first_property(event_properties, ("DTSTART",))
    if dtstart_property is None:
        raise ValueError("VEVENT is missing DTSTART.")
    dtend_property = _find_first_property(event_properties, ("DTEND",))
    summary_property = _find_first_property(event_properties, ("SUMMARY",))
    alt_description_property = _find_first_property(event_properties, ("X-ALT-DESC",))

    return ParsedCalendarEvent(
        uid=uid_property.value if uid_property is not None else None,
        starts_at=_resolve_component_datetime(
            component=component,
            property_name="DTSTART",
        ),
        ends_at=(
            _resolve_component_datetime(
                component=component,
                property_name="DTEND",
            )
            if dtend_property is not None
            else None
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
    properties: tuple[CalendarParsedProperty, ...],
    names: tuple[str, ...],
) -> CalendarParsedProperty | None:
    normalized_names = {name.upper() for name in names}
    for property_value in properties:
        if property_value.name.upper() in normalized_names:
            return property_value
    return None


def _build_parsed_property(*, name: str, value: object) -> CalendarParsedProperty:
    parameters = getattr(value, "params", {})
    return CalendarParsedProperty(
        name=name.upper(),
        value=_serialize_property_value(value),
        parameters=tuple(
            (str(parameter_name).upper(), str(parameter_value))
            for parameter_name, parameter_value in parameters.items()
        ),
    )


def _serialize_property_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "dt") and hasattr(value, "to_ical"):
        serialized = value.to_ical()
        if isinstance(serialized, bytes):
            return serialized.decode("utf-8")
        return str(serialized)
    return str(value)


def _resolve_component_datetime(
    *,
    component,
    property_name: str,
) -> datetime:
    decoded_value = component.decoded(property_name)
    resolved_datetime = _coerce_datetime(decoded_value)
    if resolved_datetime.tzinfo is not None:
        return resolved_datetime

    return resolved_datetime.replace(tzinfo=UTC)


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=UTC)
    raise TypeError(f"Unsupported calendar datetime value '{value!r}'.")


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
