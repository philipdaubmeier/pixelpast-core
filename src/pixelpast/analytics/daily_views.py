"""Derived-domain metadata for reusable daily exploration views."""

from __future__ import annotations

from dataclasses import dataclass

from pixelpast.persistence.models import (
    DAILY_AGGREGATE_OVERALL_SOURCE_TYPE,
    DAILY_AGGREGATE_SCOPE_OVERALL,
    DAILY_AGGREGATE_SCOPE_SOURCE_TYPE,
)


@dataclass(slots=True, frozen=True)
class DailyView:
    """Derived metadata describing one reusable daily aggregate view."""

    aggregate_scope: str
    source_type: str | None
    label: str
    description: str
    metadata_json: dict[str, object]


def build_daily_view(
    *,
    aggregate_scope: str,
    source_type: str,
) -> DailyView:
    """Return deterministic metadata for one daily aggregate identity."""

    if aggregate_scope == DAILY_AGGREGATE_SCOPE_OVERALL:
        return DailyView(
            aggregate_scope=aggregate_scope,
            source_type=None,
            label="Activity",
            description="Default heat intensity across all timeline sources.",
            metadata_json={
                "score_version": "v2",
                "score_formula": "activity_score = total_events + media_count",
                "summary_version": "v1",
                "source_partitioning": "events use source.type; assets use media_type",
            },
        )

    if aggregate_scope != DAILY_AGGREGATE_SCOPE_SOURCE_TYPE:
        raise ValueError(f"Unsupported daily view scope: {aggregate_scope}")

    if source_type == DAILY_AGGREGATE_OVERALL_SOURCE_TYPE:
        raise ValueError("Source-scoped daily views require a concrete source type")

    normalized_source_type = source_type.replace("_", " ").strip()
    label = normalized_source_type.title()
    return DailyView(
        aggregate_scope=aggregate_scope,
        source_type=source_type,
        label=label,
        description=f"Highlights days with {normalized_source_type} activity.",
        metadata_json={
            "score_version": "v2",
            "score_formula": "activity_score = total_events + media_count",
            "summary_version": "v1",
            "source_partitioning": "events use source.type; assets use media_type",
        },
    )
