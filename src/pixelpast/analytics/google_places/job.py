"""Google Places derive job composition root."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from pixelpast.analytics.google_places.client import (
    GooglePlacesClient,
    GooglePlacesClientError,
    GooglePlacesClientHttpError,
)
from pixelpast.analytics.google_places.loading import GooglePlacesCanonicalLoader
from pixelpast.analytics.google_places.persistence import GooglePlacesPersister
from pixelpast.analytics.google_places.progress import (
    GOOGLE_PLACES_JOB_NAME,
    GooglePlacesProgressTracker,
)
from pixelpast.analytics.google_places.provider import (
    GooglePlacesProviderSourceResolver,
)
from pixelpast.analytics.lifecycle import DeriveRunCoordinator
from pixelpast.persistence.repositories import PlaceRepository, SourceRepository
from pixelpast.shared.progress import JobProgressCallback
from pixelpast.shared.runtime import RuntimeContext
from pixelpast.shared.settings import Settings


@dataclass(slots=True, frozen=True)
class GooglePlacesJobResult:
    """Summary returned by the Google Places derive job."""

    run_id: int
    mode: str
    status: str
    scanned_event_count: int
    qualifying_event_count: int
    unique_place_id_count: int
    remote_fetch_count: int
    cached_reuse_count: int
    inserted_place_count: int
    updated_place_count: int
    unchanged_place_count: int
    inserted_event_place_link_count: int
    updated_event_place_link_count: int
    unchanged_event_place_link_count: int
    warning_messages: tuple[str, ...] = ()
    info_messages: tuple[str, ...] = ()


class GooglePlacesJob:
    """Resolve reusable derived place records from canonical event payloads."""

    def __init__(
        self,
        *,
        loader: GooglePlacesCanonicalLoader | None = None,
        provider_source_resolver: GooglePlacesProviderSourceResolver | None = None,
        persister: GooglePlacesPersister | None = None,
        lifecycle: DeriveRunCoordinator | None = None,
        client_factory: Callable[[Settings], GooglePlacesClient] | None = None,
        refreshed_at_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._loader = loader or GooglePlacesCanonicalLoader()
        self._provider_source_resolver = (
            provider_source_resolver or GooglePlacesProviderSourceResolver()
        )
        self._persister = persister or GooglePlacesPersister()
        self._lifecycle = lifecycle or DeriveRunCoordinator()
        self._client_factory = client_factory or _build_google_places_client
        self._refreshed_at_factory = refreshed_at_factory or _utc_now

    def run(
        self,
        *,
        runtime: RuntimeContext,
        start_date: date | None = None,
        end_date: date | None = None,
        max_place_ids: int | None = None,
        progress_callback: JobProgressCallback | None = None,
    ) -> GooglePlacesJobResult:
        """Resolve provider place snapshots and event-place links."""

        _validate_options(
            start_date=start_date,
            end_date=end_date,
            max_place_ids=max_place_ids,
        )
        client = self._client_factory(runtime.settings)

        run_id = self._lifecycle.create_run(
            runtime=runtime,
            job=GOOGLE_PLACES_JOB_NAME,
            mode="full",
        )
        progress = GooglePlacesProgressTracker(
            run_id=run_id,
            runtime=runtime,
            callback=progress_callback,
        )
        session = runtime.session_factory()
        place_repository = PlaceRepository(session)
        source_repository = SourceRepository(session)

        try:
            warning_messages: list[str] = []
            info_messages: list[str] = []
            progress.start_collecting()
            provider_source = self._provider_source_resolver.resolve(
                repository=source_repository
            ).source
            plan = self._loader.build_plan(
                repository=place_repository,
                provider_source_id=provider_source.id,
                refresh_max_age=runtime.settings.google_places_refresh_max_age,
                max_place_ids=max_place_ids,
            )
            progress.mark_collecting_completed(
                scanned_event_count=plan.scanned_event_count,
                candidate_event_count=plan.candidate_event_count,
                unique_place_id_count=plan.unique_place_id_count,
                cached_reuse_count=len(plan.fresh_cached_place_ids),
            )
            progress.finish_phase()

            progress.start_fetching(total_place_count=len(plan.place_ids_requiring_refresh))
            fetched_places_by_place_id = {}
            skipped_place_ids: set[str] = set()
            for place_id in plan.place_ids_requiring_refresh:
                try:
                    fetched_places_by_place_id[place_id] = client.fetch_place(
                        place_id=place_id
                    )
                    progress.mark_place_fetched()
                except GooglePlacesClientHttpError as error:
                    if error.status_code != 404:
                        raise
                    refreshed_snapshot = _try_refresh_obsolete_place_id(
                        client=client,
                        place_id=place_id,
                    )
                    if refreshed_snapshot is None:
                        skipped_place_ids.add(place_id)
                        warning_messages.append(
                            "Skipping obsolete Google Place ID "
                            f"{place_id} because it could not be refreshed."
                        )
                        progress.mark_place_skipped()
                        continue
                    fetched_places_by_place_id[place_id] = refreshed_snapshot
                    progress.mark_place_fetched()
                    if refreshed_snapshot.external_id != place_id:
                        info_messages.append(
                            "Refreshed Google Place ID "
                            f"{place_id} -> {refreshed_snapshot.external_id}"
                        )
            progress.finish_phase()

            effective_plan = _exclude_skipped_place_ids(
                plan=plan,
                skipped_place_ids=skipped_place_ids,
            )
            progress.start_persisting(
                total_write_count=(
                    len(effective_plan.place_ids_requiring_refresh)
                    + len(effective_plan.candidate_events)
                )
            )
            persistence_result = self._persister.persist(
                repository=place_repository,
                provider_source_id=provider_source.id,
                plan=effective_plan,
                fetched_places_by_place_id=fetched_places_by_place_id,
                refreshed_at=self._refreshed_at_factory(),
            )
            session.commit()
            progress.mark_persisted(
                place_write_count=len(plan.place_ids_requiring_refresh),
                link_write_count=len(plan.candidate_events),
                inserted_place_count=persistence_result.inserted_place_count,
                updated_place_count=persistence_result.updated_place_count,
                unchanged_place_count=persistence_result.unchanged_place_count,
                inserted_event_place_link_count=(
                    persistence_result.inserted_event_place_link_count
                ),
                updated_event_place_link_count=(
                    persistence_result.updated_event_place_link_count
                ),
                unchanged_event_place_link_count=(
                    persistence_result.unchanged_event_place_link_count
                ),
            )
            progress.finish_phase()
            progress.finish_run(status="completed")
            return GooglePlacesJobResult(
                run_id=run_id,
                mode="full",
                status="completed",
                scanned_event_count=plan.scanned_event_count,
                qualifying_event_count=effective_plan.candidate_event_count,
                unique_place_id_count=effective_plan.unique_place_id_count,
                remote_fetch_count=(
                    len(effective_plan.place_ids_requiring_refresh)
                    + len(skipped_place_ids)
                ),
                cached_reuse_count=len(effective_plan.fresh_cached_place_ids),
                inserted_place_count=persistence_result.inserted_place_count,
                updated_place_count=persistence_result.updated_place_count,
                unchanged_place_count=persistence_result.unchanged_place_count,
                inserted_event_place_link_count=(
                    persistence_result.inserted_event_place_link_count
                ),
                updated_event_place_link_count=(
                    persistence_result.updated_event_place_link_count
                ),
                unchanged_event_place_link_count=(
                    persistence_result.unchanged_event_place_link_count
                ),
                warning_messages=tuple(warning_messages),
                info_messages=tuple(info_messages),
            )
        except Exception:
            session.rollback()
            progress.mark_failed_operation()
            progress.fail_run()
            raise
        finally:
            session.close()


def _build_google_places_client(settings: Settings) -> GooglePlacesClient:
    api_key = settings.google_places_api_key
    if api_key is None or not api_key.strip():
        raise ValueError("Google Places derivation requires PIXELPAST_GOOGLE_PLACES_API_KEY.")

    return GooglePlacesClient(
        api_key=api_key,
        language_code=settings.google_places_language_code,
        region_code=settings.google_places_region_code,
    )


def _validate_options(
    *,
    start_date: date | None,
    end_date: date | None,
    max_place_ids: int | None,
) -> None:
    if start_date is None and end_date is None:
        pass
    else:
        raise ValueError(
            "Google Places derivation does not support --start-date/--end-date."
        )
    if max_place_ids is not None and max_place_ids < 1:
        raise ValueError("Google Places derivation requires --top-place-ids >= 1.")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _try_refresh_obsolete_place_id(
    *,
    client: GooglePlacesClient,
    place_id: str,
) -> GooglePlaceSnapshot | None:
    try:
        refreshed_place_id = client.refresh_place_id(place_id=place_id)
        return client.fetch_place(place_id=refreshed_place_id)
    except GooglePlacesClientError:
        return None


def _exclude_skipped_place_ids(
    *,
    plan,
    skipped_place_ids: set[str],
):
    if not skipped_place_ids:
        return plan

    candidate_events = tuple(
        candidate
        for candidate in plan.candidate_events
        if candidate.google_place_id not in skipped_place_ids
    )
    candidates_by_place_id = {
        place_id: candidates
        for place_id, candidates in plan.candidates_by_place_id.items()
        if place_id not in skipped_place_ids
    }
    fresh_cached_place_ids = tuple(
        place_id
        for place_id in plan.fresh_cached_place_ids
        if place_id not in skipped_place_ids
    )
    place_ids_requiring_refresh = tuple(
        place_id
        for place_id in plan.place_ids_requiring_refresh
        if place_id not in skipped_place_ids
    )
    cached_places_by_place_id = {
        place_id: place
        for place_id, place in plan.cached_places_by_place_id.items()
        if place_id not in skipped_place_ids
    }
    return type(plan)(
        scanned_event_count=plan.scanned_event_count,
        candidate_event_count=len(candidate_events),
        unique_place_id_count=(
            len(fresh_cached_place_ids) + len(place_ids_requiring_refresh)
        ),
        candidate_events=candidate_events,
        candidates_by_place_id=candidates_by_place_id,
        cached_places_by_place_id=cached_places_by_place_id,
        fresh_cached_place_ids=fresh_cached_place_ids,
        place_ids_requiring_refresh=place_ids_requiring_refresh,
    )


__all__ = [
    "GOOGLE_PLACES_JOB_NAME",
    "GooglePlacesJob",
    "GooglePlacesJobResult",
    "GooglePlacesClientError",
]
