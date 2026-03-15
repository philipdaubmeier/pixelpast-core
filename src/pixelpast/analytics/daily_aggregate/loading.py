"""Canonical input loading for the daily aggregate derive job."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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

    def load_event_inputs(
        self,
        *,
        repository: CanonicalTimelineRepository,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalEventAggregateInput]:
        """Return canonical event contributions for the requested rebuild window."""

        return repository.list_event_inputs(
            start_date=start_date,
            end_date=end_date,
        )

    def load_asset_inputs(
        self,
        *,
        repository: CanonicalTimelineRepository,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalAssetAggregateInput]:
        """Return canonical asset contributions for the requested rebuild window."""

        return repository.list_asset_inputs(
            start_date=start_date,
            end_date=end_date,
        )

    def load_tag_inputs(
        self,
        *,
        repository: CanonicalTimelineRepository,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalTagAggregateInput]:
        """Return canonical tag contributions for the requested rebuild window."""

        return [
            *repository.list_event_tag_inputs(
                start_date=start_date,
                end_date=end_date,
            ),
            *repository.list_asset_tag_inputs(
                start_date=start_date,
                end_date=end_date,
            ),
        ]

    def load_person_inputs(
        self,
        *,
        repository: CanonicalTimelineRepository,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CanonicalPersonAggregateInput]:
        """Return canonical person contributions for the requested rebuild window."""

        return [
            *repository.list_event_person_inputs(
                start_date=start_date,
                end_date=end_date,
            ),
            *repository.list_asset_person_inputs(
                start_date=start_date,
                end_date=end_date,
            ),
        ]

    def load(
        self,
        *,
        repository: CanonicalTimelineRepository,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DailyAggregateCanonicalInputs:
        """Return all canonical contributions for the requested rebuild window."""

        return DailyAggregateCanonicalInputs(
            event_inputs=self.load_event_inputs(
                repository=repository,
                start_date=start_date,
                end_date=end_date,
            ),
            asset_inputs=self.load_asset_inputs(
                repository=repository,
                start_date=start_date,
                end_date=end_date,
            ),
            tag_inputs=self.load_tag_inputs(
                repository=repository,
                start_date=start_date,
                end_date=end_date,
            ),
            person_inputs=self.load_person_inputs(
                repository=repository,
                start_date=start_date,
                end_date=end_date,
            ),
        )
