"""Daily aggregate derivation job.

The scoring formula intentionally stays simple and transparent:

    activity_score = total_events + media_count

Connector-aware v2 rows still use the same score, but partition canonical input
by source identity before also materializing an explicit overall rollup.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pixelpast.persistence.models import (
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
)
from pixelpast.persistence.repositories.daily_aggregates import (
    CanonicalAssetAggregateInput,
    CanonicalEventAggregateInput,
    CanonicalPersonAggregateInput,
    CanonicalTagAggregateInput,
    CanonicalTimelineRepository,
    DailyAggregateRepository,
    DailyAggregateSnapshot,
)
from pixelpast.shared.runtime import RuntimeContext

_SCORE_METADATA = {
    "score_version": "v2",
    "score_formula": "activity_score = total_events + media_count",
    "summary_version": "v1",
    "source_partitioning": "events use source.type; assets use media_type",
}


@dataclass(slots=True, frozen=True)
class DailyAggregateJobResult:
    """Summary returned by the daily aggregate derivation job."""

    mode: str
    start_date: date | None
    end_date: date | None
    aggregate_count: int
    total_events: int
    media_count: int


@dataclass(slots=True)
class _AggregateState:
    """Mutable accumulator for one derived aggregate row."""

    total_events: int = 0
    media_count: int = 0
    tags: Counter[tuple[str, str]] | None = None
    persons: Counter[tuple[int, str, str | None]] | None = None
    locations: Counter[tuple[str, float, float]] | None = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = Counter()
        if self.persons is None:
            self.persons = Counter()
        if self.locations is None:
            self.locations = Counter()


class DailyAggregateJob:
    """Rebuild daily aggregate rows from canonical events and assets."""

    def run(
        self,
        *,
        runtime: RuntimeContext,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DailyAggregateJobResult:
        """Recompute daily aggregates for a full rebuild or an inclusive range."""

        _validate_date_range(start_date=start_date, end_date=end_date)

        session = runtime.session_factory()
        canonical_repository = CanonicalTimelineRepository(session)
        aggregate_repository = DailyAggregateRepository(session)

        try:
            event_inputs = canonical_repository.list_event_inputs(
                start_date=start_date,
                end_date=end_date,
            )
            asset_inputs = canonical_repository.list_asset_inputs(
                start_date=start_date,
                end_date=end_date,
            )
            tag_inputs = [
                *canonical_repository.list_event_tag_inputs(
                    start_date=start_date,
                    end_date=end_date,
                ),
                *canonical_repository.list_asset_tag_inputs(
                    start_date=start_date,
                    end_date=end_date,
                ),
            ]
            person_inputs = [
                *canonical_repository.list_event_person_inputs(
                    start_date=start_date,
                    end_date=end_date,
                ),
                *canonical_repository.list_asset_person_inputs(
                    start_date=start_date,
                    end_date=end_date,
                ),
            ]
            aggregates = _build_snapshots(
                event_inputs=event_inputs,
                asset_inputs=asset_inputs,
                tag_inputs=tag_inputs,
                person_inputs=person_inputs,
            )

            if start_date is None and end_date is None:
                aggregate_repository.replace_all(aggregates=aggregates)
                mode = "full"
                resolved_start_date = min(
                    (aggregate.date for aggregate in aggregates),
                    default=None,
                )
                resolved_end_date = max(
                    (aggregate.date for aggregate in aggregates),
                    default=None,
                )
            else:
                aggregate_repository.replace_range(
                    start_date=start_date,
                    end_date=end_date,
                    aggregates=aggregates,
                )
                mode = "range"
                resolved_start_date = start_date
                resolved_end_date = end_date

            session.commit()
            return DailyAggregateJobResult(
                mode=mode,
                start_date=resolved_start_date,
                end_date=resolved_end_date,
                aggregate_count=len(aggregates),
                total_events=len(event_inputs),
                media_count=len(asset_inputs),
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _build_snapshots(
    *,
    event_inputs: list[CanonicalEventAggregateInput],
    asset_inputs: list[CanonicalAssetAggregateInput],
    tag_inputs: list[CanonicalTagAggregateInput],
    person_inputs: list[CanonicalPersonAggregateInput],
) -> list[DailyAggregateSnapshot]:
    """Build sorted repository snapshots from canonical UTC day contributions."""

    states: dict[tuple[date, str], _AggregateState] = {}

    for event_input in event_inputs:
        for aggregate_key in _iter_aggregate_keys(
            day=event_input.day,
            source_type=event_input.source_type,
        ):
            state = states.setdefault(aggregate_key, _AggregateState())
            state.total_events += 1
            location_key = _build_event_location_key(event_input)
            if location_key is not None:
                state.locations[location_key] += 1

    for asset_input in asset_inputs:
        for aggregate_key in _iter_aggregate_keys(
            day=asset_input.day,
            source_type=asset_input.source_type,
        ):
            state = states.setdefault(aggregate_key, _AggregateState())
            state.media_count += 1
            location_key = _build_asset_location_key(asset_input)
            if location_key is not None:
                state.locations[location_key] += 1

    for tag_input in tag_inputs:
        for aggregate_key in _iter_aggregate_keys(
            day=tag_input.day,
            source_type=tag_input.source_type,
        ):
            state = states.setdefault(aggregate_key, _AggregateState())
            state.tags[(tag_input.path, tag_input.label)] += 1

    for person_input in person_inputs:
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
                aggregate_scope=aggregate_scope,
                source_type=source_type,
                total_events=state.total_events,
                media_count=state.media_count,
                activity_score=_calculate_activity_score(
                    total_events=state.total_events,
                    media_count=state.media_count,
                ),
                tag_summary_json=_build_tag_summary(state.tags),
                person_summary_json=_build_person_summary(state.persons),
                location_summary_json=_build_location_summary(state.locations),
                metadata_json=dict(_SCORE_METADATA),
            )
        )

    return snapshots


def _calculate_activity_score(*, total_events: int, media_count: int) -> int:
    """Return the documented activity score for a single aggregate row."""

    return total_events + media_count


def _validate_date_range(*, start_date: date | None, end_date: date | None) -> None:
    """Ensure the job runs either in full rebuild mode or with a closed range."""

    if (start_date is None) != (end_date is None):
        raise ValueError(
            "Daily aggregate derivation requires both start_date and end_date "
            "when running a range recomputation."
        )

    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("Daily aggregate derivation requires start_date <= end_date.")


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


def _build_event_location_key(
    event_input: CanonicalEventAggregateInput,
) -> tuple[str, float, float] | None:
    """Return a normalized location key for an event contribution."""

    if event_input.latitude is None or event_input.longitude is None:
        return None

    title = event_input.title.strip()
    label = title if title else event_input.event_type
    return (label, event_input.latitude, event_input.longitude)


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
