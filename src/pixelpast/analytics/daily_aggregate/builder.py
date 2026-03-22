"""Pure snapshot construction for daily aggregate derivation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
import math
from pathlib import Path
import re
from typing import Any

from pixelpast.analytics.daily_aggregate.loading import (
    DailyAggregateCanonicalInputs,
)
from pixelpast.analytics.daily_views import (
    TIMELINE_ACTIVITY_SOURCE_TYPE,
    TIMELINE_VISIT_SOURCE_TYPE,
    WORKDAYS_VACATION_SOURCE_TYPE,
    build_daily_view,
)
from pixelpast.persistence.models import (
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
)
from pixelpast.persistence.repositories.daily_aggregates import (
    CanonicalAssetAggregateInput,
    CanonicalEventAggregateInput,
    CanonicalEventPlaceAggregateInput,
    DailyAggregateSnapshot,
)

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
_TIMELINE_EVENT_TYPES = {
    TIMELINE_VISIT_SOURCE_TYPE,
    TIMELINE_ACTIVITY_SOURCE_TYPE,
}


@dataclass(slots=True, frozen=True)
class _DirectColorSelection:
    """Deterministic workdays-vacation day payload chosen for one aggregate row."""

    timestamp_start_sort_key: str
    title: str
    color_value: str


@dataclass(slots=True)
class _AggregateState:
    """Mutable accumulator for one derived aggregate row."""

    total_events: int = 0
    media_count: int = 0
    tags: Counter[tuple[str, str]] | None = None
    persons: Counter[tuple[int, str, str | None]] | None = None
    locations: Counter[tuple[str, float, float]] | None = None
    visit_locations: Counter[tuple[str, float, float]] | None = None
    activity_locations: list[tuple[float, float]] | None = None
    activity_location_identities: set[tuple[float, float]] | None = None
    activity_distance_meters: float = 0.0
    movement_distance_meters_by_label: Counter[str] | None = None
    direct_color_selection: _DirectColorSelection | None = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = Counter()
        if self.persons is None:
            self.persons = Counter()
        if self.locations is None:
            self.locations = Counter()
        if self.visit_locations is None:
            self.visit_locations = Counter()
        if self.activity_locations is None:
            self.activity_locations = []
        if self.activity_location_identities is None:
            self.activity_location_identities = set()
        if self.movement_distance_meters_by_label is None:
            self.movement_distance_meters_by_label = Counter()


def build_daily_aggregate_snapshots(
    inputs: DailyAggregateCanonicalInputs,
) -> list[DailyAggregateSnapshot]:
    """Build sorted repository snapshots from canonical UTC day contributions."""

    states: dict[tuple[date, str], _AggregateState] = {}

    for event_input in inputs.event_inputs:
        for aggregate_key in _iter_event_aggregate_keys(event_input):
            state = states.setdefault(aggregate_key, _AggregateState())
            state.total_events += 1
            _merge_direct_color_selection(
                state=state,
                aggregate_key=aggregate_key,
                event_input=event_input,
            )
            _merge_event_location(state=state, aggregate_key=aggregate_key, event_input=event_input)
            _merge_activity_metrics(
                state=state,
                aggregate_key=aggregate_key,
                event_input=event_input,
            )

    for event_place_input in inputs.event_place_inputs:
        for aggregate_key in _iter_event_place_aggregate_keys(event_place_input):
            state = states.setdefault(aggregate_key, _AggregateState())
            visit_location_key = _build_visit_location_key(event_place_input)
            if visit_location_key is not None:
                state.visit_locations[visit_location_key] += 1

    for asset_input in inputs.asset_inputs:
        for aggregate_key in _iter_aggregate_keys(
            day=asset_input.day,
            source_type=asset_input.source_type,
        ):
            state = states.setdefault(aggregate_key, _AggregateState())
            state.media_count += 1
            location_key = _build_asset_location_key(asset_input)
            if location_key is not None:
                state.locations[location_key] += 1

    for tag_input in inputs.tag_inputs:
        for aggregate_key in _iter_aggregate_keys(
            day=tag_input.day,
            source_type=tag_input.source_type,
        ):
            state = states.setdefault(aggregate_key, _AggregateState())
            state.tags[(tag_input.path, tag_input.label)] += 1

    for person_input in inputs.person_inputs:
        for aggregate_key in _iter_aggregate_keys(
            day=person_input.day,
            source_type=person_input.source_type,
        ):
            state = states.setdefault(aggregate_key, _AggregateState())
            state.persons[
                (person_input.person_id, person_input.name, person_input.role)
            ] += 1

    snapshots: list[DailyAggregateSnapshot] = []
    for (aggregate_date, source_type), state in sorted(
        states.items(),
        key=_sort_aggregate_key,
    ):
        aggregate_scope = (
            DAILY_AGGREGATE_SCOPE_OVERALL
            if source_type == DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
            else DAILY_AGGREGATE_SCOPE_SOURCE_TYPE
        )
        snapshots.append(
            DailyAggregateSnapshot(
                date=aggregate_date,
                daily_view=build_daily_view(
                    aggregate_scope=aggregate_scope,
                    source_type=source_type,
                ),
                total_events=state.total_events,
                media_count=state.media_count,
                activity_score=_resolve_activity_score(
                    source_type=source_type,
                    total_events=state.total_events,
                    media_count=state.media_count,
                    activity_distance_meters=state.activity_distance_meters,
                ),
                color_value=(
                    state.direct_color_selection.color_value
                    if state.direct_color_selection is not None
                    else None
                ),
                title=_resolve_title(
                    source_type=source_type,
                    state=state,
                ),
                tag_summary_json=_build_tag_summary(state.tags),
                person_summary_json=_build_person_summary(state.persons),
                location_summary_json=_resolve_location_summary(
                    source_type=source_type,
                    state=state,
                ),
            )
        )

    return snapshots


def _calculate_activity_score(*, total_events: int, media_count: int) -> int:
    """Return the documented activity score for a single aggregate row."""

    return total_events + media_count


def _resolve_activity_score(
    *,
    source_type: str,
    total_events: int,
    media_count: int,
    activity_distance_meters: float,
) -> int:
    """Return the score contract for the aggregate identity being built."""

    if source_type == TIMELINE_ACTIVITY_SOURCE_TYPE:
        return _meters_to_display_kilometers(activity_distance_meters)
    return _calculate_activity_score(
        total_events=total_events,
        media_count=media_count,
    )


def _iter_aggregate_keys(
    *,
    day: date,
    source_type: str,
) -> tuple[tuple[date, str], ...]:
    """Return source-scoped and overall aggregate keys for one canonical item."""

    return (
        (day, source_type),
        (day, DAILY_AGGREGATE_OVERALL_SOURCE_TYPE),
    )


def _iter_event_aggregate_keys(
    event_input: CanonicalEventAggregateInput,
) -> tuple[tuple[date, str], ...]:
    """Return all aggregate identities one canonical event contributes to."""

    if event_input.event_type in _TIMELINE_EVENT_TYPES:
        aggregate_keys = [
            (event_input.day, DAILY_AGGREGATE_OVERALL_SOURCE_TYPE),
        ]
        aggregate_keys.append((event_input.day, event_input.event_type))
        return tuple(aggregate_keys)

    return _iter_aggregate_keys(
        day=event_input.day,
        source_type=event_input.source_type,
    )


def _iter_event_place_aggregate_keys(
    event_place_input: CanonicalEventPlaceAggregateInput,
) -> tuple[tuple[date, str], ...]:
    """Return aggregate identities that consume derived event-place links."""

    if event_place_input.event_type != TIMELINE_VISIT_SOURCE_TYPE:
        return ()
    return ((event_place_input.day, TIMELINE_VISIT_SOURCE_TYPE),)


def _sort_aggregate_key(
    item: tuple[tuple[date, str], _AggregateState],
) -> tuple[date, int, str]:
    """Sort overall rows before source-scoped rows for a stable rebuild order."""

    (aggregate_date, source_type), _state = item
    is_overall = source_type == DAILY_AGGREGATE_OVERALL_SOURCE_TYPE
    return (aggregate_date, 0 if is_overall else 1, source_type)


def _build_tag_summary(
    counter: Counter[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Return a deterministic tag summary payload."""

    return [
        {"path": path, "label": label, "count": count}
        for (path, label), count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1].casefold()),
        )
    ]


def _build_person_summary(
    counter: Counter[tuple[int, str, str | None]],
) -> list[dict[str, Any]]:
    """Return a deterministic person summary payload."""

    return [
        {
            "person_id": person_id,
            "name": name,
            "role": role,
            "count": count,
        }
        for (person_id, name, role), count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0][1].casefold(), item[0][0]),
        )
    ]


def _build_location_summary(
    counter: Counter[tuple[str, float, float]],
) -> list[dict[str, Any]]:
    """Return a deterministic location summary payload."""

    return [
        {
            "label": label,
            "latitude": latitude,
            "longitude": longitude,
            "count": count,
        }
        for (label, latitude, longitude), count in sorted(
            counter.items(),
            key=lambda item: (
                -item[1],
                item[0][0].casefold(),
                item[0][1],
                item[0][2],
            ),
        )
    ]


def _build_activity_location_summary(
    points: list[tuple[float, float]],
) -> list[dict[str, Any]]:
    """Return raw coordinate points without labels or timestamps."""

    return [
        {
            "latitude": latitude,
            "longitude": longitude,
        }
        for latitude, longitude in points
    ]


def _build_event_location_key(
    event_input: CanonicalEventAggregateInput,
) -> tuple[str, float, float] | None:
    """Return a normalized location key for an event contribution."""

    if event_input.latitude is None or event_input.longitude is None:
        return None

    title = event_input.title.strip()
    label = title if title else event_input.event_type
    return (label, event_input.latitude, event_input.longitude)


def _build_visit_location_key(
    event_place_input: CanonicalEventPlaceAggregateInput,
) -> tuple[str, float, float] | None:
    """Return a place-backed visit location key for aggregation."""

    if event_place_input.latitude is None or event_place_input.longitude is None:
        return None
    label = (
        event_place_input.display_name.strip()
        if isinstance(event_place_input.display_name, str)
        and event_place_input.display_name.strip()
        else "Place"
    )
    return (label, event_place_input.latitude, event_place_input.longitude)


def _merge_event_location(
    *,
    state: _AggregateState,
    aggregate_key: tuple[date, str],
    event_input: CanonicalEventAggregateInput,
) -> None:
    """Merge generic point-based event locations, excluding timeline-specific views."""

    _aggregate_date, source_type = aggregate_key
    if source_type in {TIMELINE_VISIT_SOURCE_TYPE, TIMELINE_ACTIVITY_SOURCE_TYPE}:
        return

    location_key = _build_event_location_key(event_input)
    if location_key is not None:
        state.locations[location_key] += 1


def _merge_activity_metrics(
    *,
    state: _AggregateState,
    aggregate_key: tuple[date, str],
    event_input: CanonicalEventAggregateInput,
) -> None:
    """Merge movement distance, title, and waypoint data for timeline activity rows."""

    _aggregate_date, source_type = aggregate_key
    if source_type != TIMELINE_ACTIVITY_SOURCE_TYPE:
        return
    if event_input.event_type != TIMELINE_ACTIVITY_SOURCE_TYPE:
        return

    distance_meters = _extract_distance_meters(event_input.raw_payload)
    if distance_meters is not None:
        normalized_label = _normalize_activity_label(event_input.title)
        state.activity_distance_meters += distance_meters
        state.movement_distance_meters_by_label[normalized_label] += distance_meters

    for latitude, longitude in _extract_path_points(event_input.raw_payload):
        identity = (latitude, longitude)
        if identity in state.activity_location_identities:
            continue
        state.activity_location_identities.add(identity)
        state.activity_locations.append(identity)


def _merge_direct_color_selection(
    *,
    state: _AggregateState,
    aggregate_key: tuple[date, str],
    event_input: CanonicalEventAggregateInput,
) -> None:
    """Persist deterministic direct-color data for the workdays-vacation view only."""

    _aggregate_date, source_type = aggregate_key
    if source_type != WORKDAYS_VACATION_SOURCE_TYPE:
        return
    if event_input.event_type != WORKDAYS_VACATION_SOURCE_TYPE:
        return

    candidate = _build_direct_color_selection(event_input)
    if candidate is None:
        return

    if (
        state.direct_color_selection is None
        or _direct_color_sort_key(candidate)
        < _direct_color_sort_key(state.direct_color_selection)
    ):
        state.direct_color_selection = candidate


def _build_direct_color_selection(
    event_input: CanonicalEventAggregateInput,
) -> _DirectColorSelection | None:
    """Return one validated direct-color selection candidate from canonical event data."""

    raw_payload = event_input.raw_payload
    if not isinstance(raw_payload, dict):
        return None

    color_value = raw_payload.get("color_value")
    if not isinstance(color_value, str):
        return None

    normalized_color_value = color_value.strip()
    if not _HEX_COLOR_PATTERN.fullmatch(normalized_color_value):
        return None

    title = _resolve_direct_color_title(event_input)
    if title is None:
        return None

    return _DirectColorSelection(
        timestamp_start_sort_key=event_input.timestamp_start.isoformat(),
        title=title,
        color_value=normalized_color_value,
    )


def _resolve_direct_color_title(event_input: CanonicalEventAggregateInput) -> str | None:
    """Return the short workdays-vacation label preserved in canonical event data."""

    title = event_input.title.strip()
    if title:
        return title

    raw_payload = event_input.raw_payload
    if not isinstance(raw_payload, dict):
        return None

    short_code = raw_payload.get("short_code")
    if isinstance(short_code, str) and short_code.strip():
        return short_code.strip()
    return None


def _direct_color_sort_key(
    selection: _DirectColorSelection,
) -> tuple[str, str, str]:
    """Sort same-day workdays-vacation conflicts by time, then title, then color."""

    return (
        selection.timestamp_start_sort_key,
        selection.title.casefold(),
        selection.color_value.casefold(),
    )


def _resolve_title(
    *,
    source_type: str,
    state: _AggregateState,
) -> str | None:
    """Return the backend-owned title for one aggregate row."""

    if source_type == TIMELINE_ACTIVITY_SOURCE_TYPE:
        return _build_activity_title(state.movement_distance_meters_by_label)
    if state.direct_color_selection is not None:
        return state.direct_color_selection.title
    return None


def _resolve_location_summary(
    *,
    source_type: str,
    state: _AggregateState,
) -> list[dict[str, Any]]:
    """Return the location summary payload for one aggregate identity."""

    if source_type == TIMELINE_VISIT_SOURCE_TYPE:
        return _build_location_summary(state.visit_locations)
    if source_type == TIMELINE_ACTIVITY_SOURCE_TYPE:
        return _build_activity_location_summary(state.activity_locations)
    return _build_location_summary(state.locations)


def _build_activity_title(distance_by_label: Counter[str]) -> str | None:
    """Return the top-three movement-mode title summary for one day."""

    if not distance_by_label:
        return None

    top_entries = sorted(
        distance_by_label.items(),
        key=lambda item: (-item[1], item[0].casefold()),
    )[:3]
    return ", ".join(
        f"{_meters_to_display_kilometers(distance_meters)} km {label}"
        for label, distance_meters in top_entries
    )


def _normalize_activity_label(value: str) -> str:
    """Return a stable activity label for grouping movement modes."""

    normalized = value.strip()
    return normalized if normalized else TIMELINE_ACTIVITY_SOURCE_TYPE


def _extract_distance_meters(raw_payload: object) -> float | None:
    """Return the canonical timeline activity distance in meters."""

    if not isinstance(raw_payload, dict):
        return None
    value = raw_payload.get("distanceMeters")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _extract_path_points(raw_payload: object) -> tuple[tuple[float, float], ...]:
    """Return canonical activity path points as latitude/longitude tuples."""

    if not isinstance(raw_payload, dict):
        return ()
    path_points = raw_payload.get("pathPoints")
    if not isinstance(path_points, list):
        return ()

    normalized_points: list[tuple[float, float]] = []
    for path_point in path_points:
        if not isinstance(path_point, dict):
            continue
        latitude = path_point.get("latitude")
        longitude = path_point.get("longitude")
        if isinstance(latitude, bool) or isinstance(longitude, bool):
            continue
        if not isinstance(latitude, (int, float)) or not isinstance(
            longitude, (int, float)
        ):
            continue
        normalized_points.append((float(latitude), float(longitude)))
    return tuple(normalized_points)


def _meters_to_display_kilometers(distance_meters: float) -> int:
    """Render meters as deterministic whole-kilometer display units."""

    if distance_meters <= 0:
        return 0
    return max(1, math.floor((distance_meters / 1000.0) + 0.5))


def _build_asset_location_key(
    asset_input: CanonicalAssetAggregateInput,
) -> tuple[str, float, float] | None:
    """Return a normalized location key for an asset contribution."""

    if asset_input.latitude is None or asset_input.longitude is None:
        return None

    return (
        _resolve_asset_location_label(asset_input),
        asset_input.latitude,
        asset_input.longitude,
    )


def _resolve_asset_location_label(asset_input: CanonicalAssetAggregateInput) -> str:
    """Resolve a stable human-readable asset location label."""

    if asset_input.summary is not None and asset_input.summary.strip():
        return asset_input.summary.strip()

    if isinstance(asset_input.metadata_json, dict):
        for key in ("label", "title", "filename", "original_filename"):
            value = asset_input.metadata_json.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    external_name = Path(asset_input.external_id).name.strip()
    if external_name:
        return external_name
    return asset_input.media_type
