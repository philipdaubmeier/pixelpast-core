"""Canonical input loading for the daily aggregate derive job."""

from __future__ import annotations

from dataclasses import dataclass

from pixelpast.persistence.repositories.daily_aggregates import (
    CanonicalAssetAggregateInput,
    CanonicalEventAggregateInput,
    CanonicalPersonAggregateInput,
    CanonicalTagAggregateInput,
    CanonicalTimelineRepository,
)


@dataclass(slots=True, frozen=True)
class DailyAggregateCanonicalInputs:
    """Canonical day contributions needed to build daily aggregate rows."""

    event_inputs: list[CanonicalEventAggregateInput]
    asset_inputs: list[CanonicalAssetAggregateInput]
    tag_inputs: list[CanonicalTagAggregateInput]
    person_inputs: list[CanonicalPersonAggregateInput]


class DailyAggregateCanonicalLoader:
    """Load canonical inputs for a full or range-scoped aggregate rebuild."""

    def load(
        self,
        *,
        repository: CanonicalTimelineRepository,
        start_date=None,
        end_date=None,
    ) -> DailyAggregateCanonicalInputs:
        """Return canonical contributions for the requested rebuild window."""

        return DailyAggregateCanonicalInputs(
            event_inputs=repository.list_event_inputs(
                start_date=start_date,
                end_date=end_date,
            ),
            asset_inputs=repository.list_asset_inputs(
                start_date=start_date,
                end_date=end_date,
            ),
            tag_inputs=[
                *repository.list_event_tag_inputs(
                    start_date=start_date,
                    end_date=end_date,
                ),
                *repository.list_asset_tag_inputs(
                    start_date=start_date,
                    end_date=end_date,
                ),
            ],
            person_inputs=[
                *repository.list_event_person_inputs(
                    start_date=start_date,
                    end_date=end_date,
                ),
                *repository.list_asset_person_inputs(
                    start_date=start_date,
                    end_date=end_date,
                ),
            ],
        )
