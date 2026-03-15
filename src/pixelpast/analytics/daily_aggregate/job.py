"""Daily aggregate derive job composition root."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from pixelpast.analytics.daily_aggregate.builder import (
    build_daily_aggregate_snapshots,
)
from pixelpast.analytics.daily_aggregate.loading import (
    DailyAggregateCanonicalInputs,
    DailyAggregateCanonicalLoader,
)
from pixelpast.analytics.daily_aggregate.persistence import (
    DailyAggregateSnapshotPersister,
)
from pixelpast.analytics.daily_aggregate.progress import (
    DAILY_AGGREGATE_JOB_NAME,
    DailyAggregateProgressTracker,
)
from pixelpast.analytics.lifecycle import DeriveRunCoordinator
from pixelpast.persistence.repositories.daily_aggregates import (
    CanonicalTimelineRepository,
    DailyAggregateRepository,
    DailyAggregateSnapshot,
)
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext


@dataclass(slots=True, frozen=True)
class DailyAggregateJobResult:
    """Summary returned by the daily aggregate derivation job."""

    run_id: int
    mode: str
    start_date: date | None
    end_date: date | None
    aggregate_count: int
    total_events: int
    media_count: int


class DailyAggregateJob:
    """Rebuild daily aggregate rows from canonical events and assets."""

    def __init__(
        self,
        *,
        loader: DailyAggregateCanonicalLoader | None = None,
        snapshot_builder: (
            Callable[[DailyAggregateCanonicalInputs], list[DailyAggregateSnapshot]]
            | None
        ) = None,
        persister: DailyAggregateSnapshotPersister | None = None,
        lifecycle: DeriveRunCoordinator | None = None,
    ) -> None:
        self._loader = loader or DailyAggregateCanonicalLoader()
        self._snapshot_builder = snapshot_builder or build_daily_aggregate_snapshots
        self._persister = persister or DailyAggregateSnapshotPersister()
        self._lifecycle = lifecycle or DeriveRunCoordinator()

    def run(
        self,
        *,
        runtime: RuntimeContext,
        start_date: date | None = None,
        end_date: date | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> DailyAggregateJobResult:
        """Recompute daily aggregates for a full rebuild or an inclusive range."""

        _validate_date_range(start_date=start_date, end_date=end_date)

        mode = _resolve_mode(start_date=start_date, end_date=end_date)
        run_id = self._lifecycle.create_run(
            runtime=runtime,
            job=DAILY_AGGREGATE_JOB_NAME,
            mode=mode,
        )
        progress = DailyAggregateProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
        )
        session = runtime.session_factory()
        canonical_repository = CanonicalTimelineRepository(session)
        aggregate_repository = DailyAggregateRepository(session)

        try:
            progress.start_loading()
            event_inputs = self._loader.load_event_inputs(
                repository=canonical_repository,
                start_date=start_date,
                end_date=end_date,
            )
            progress.mark_loading_bucket_completed()
            asset_inputs = self._loader.load_asset_inputs(
                repository=canonical_repository,
                start_date=start_date,
                end_date=end_date,
            )
            progress.mark_loading_bucket_completed()
            tag_inputs = self._loader.load_tag_inputs(
                repository=canonical_repository,
                start_date=start_date,
                end_date=end_date,
            )
            progress.mark_loading_bucket_completed()
            person_inputs = self._loader.load_person_inputs(
                repository=canonical_repository,
                start_date=start_date,
                end_date=end_date,
            )
            progress.mark_loading_bucket_completed()
            progress.finish_phase()

            inputs = DailyAggregateCanonicalInputs(
                event_inputs=event_inputs,
                asset_inputs=asset_inputs,
                tag_inputs=tag_inputs,
                person_inputs=person_inputs,
            )
            total_input_count = (
                len(inputs.event_inputs)
                + len(inputs.asset_inputs)
                + len(inputs.tag_inputs)
                + len(inputs.person_inputs)
            )

            progress.start_building(total_input_count=total_input_count)
            aggregates = self._snapshot_builder(inputs)
            progress.mark_build_completed(total_input_count=total_input_count)
            progress.finish_phase()

            progress.start_persisting(aggregate_count=len(aggregates))
            persistence_result = self._persister.persist(
                repository=aggregate_repository,
                start_date=start_date,
                end_date=end_date,
                aggregates=aggregates,
            )
            session.commit()
            progress.mark_persisted(aggregate_count=len(aggregates))
            progress.finish_phase()
            progress.finish_run(status="completed")
            return DailyAggregateJobResult(
                run_id=run_id,
                mode=persistence_result.mode,
                start_date=persistence_result.start_date,
                end_date=persistence_result.end_date,
                aggregate_count=len(aggregates),
                total_events=len(inputs.event_inputs),
                media_count=len(inputs.asset_inputs),
            )
        except Exception:
            session.rollback()
            progress.fail_run()
            raise
        finally:
            session.close()


def _validate_date_range(*, start_date: date | None, end_date: date | None) -> None:
    """Ensure the job runs either in full rebuild mode or with a closed range."""

    if (start_date is None) != (end_date is None):
        raise ValueError(
            "Daily aggregate derivation requires both start_date and end_date "
            "when running a range recomputation."
        )

    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("Daily aggregate derivation requires start_date <= end_date.")


def _resolve_mode(*, start_date: date | None, end_date: date | None) -> str:
    """Return the persisted run mode for the requested derive window."""

    return "range" if start_date is not None and end_date is not None else "full"
