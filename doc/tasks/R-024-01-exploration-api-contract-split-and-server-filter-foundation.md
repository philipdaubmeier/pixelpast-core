# R-024-01 - Exploration API Contract Split and Server-Filter Foundation

## Goal

Reshape the exploration-facing API so the calendar grid, bootstrap catalogs,
and day-context loading have explicit and separate contracts.

The main architectural change is that persistent filtering should no longer
depend on client-side filtering over preloaded per-day summaries. Instead, the
API should become the authoritative place where persistent timeline filters are
applied.

This task establishes the backend contract and implementation needed for that
direction.

## Reasoning

The current client-side filtering approach is only viable while filters remain
very shallow, for example simple person or tag selection against already loaded
day summaries.

That approach does not scale well to future filter types such as:

- location bounding boxes
- polygon-based geographic filters
- radius / distance queries
- database-backed full-dataset filename filters
- richer temporal and semantic predicates

These filters are inherently better executed on the server and often directly on
the database. The browser should not be expected to preload enough data to
reproduce those queries locally.

Persistent filters also change only through deliberate user interaction. That
makes server roundtrips acceptable and keeps the client projection model simpler
and more correct.

Hover interaction is different. Hover must remain fast while the pointer moves
across many cells, so bounded day-context data should still be prefetched and
resolved client-side for the currently visible range.

The resulting principle is:

- persistent filters are server-side
- hover context remains client-side once a bounded context range is loaded

## Dependencies

- `R-023-03`
- `R-015`

## Scope

### Split Exploration Responsibilities into Explicit Endpoints

Replace the overloaded exploration bootstrap shape with separate contracts for:

- shell/bootstrap metadata
- grid activity data
- bounded day-context data

Preferred endpoint structure:

- `GET /exploration/bootstrap`
- `GET /exploration`
- `GET /days/context`

If path naming needs to vary slightly, the separation of responsibility is the
mandatory part.

### Define a Minimal Grid Contract

The grid-facing exploration endpoint should return only what is needed to render
day activity state.

The primary day payload should include only:

- `date`
- `activity_score`
- `color_value`
- `has_data`

Do not include per-day persons, tags, locations, connector summaries, or other
heavy semantic day payloads in this endpoint.

This endpoint remains strictly derived-only and must read from
`DailyAggregate`.

### Move Persistent Filtering to the Server Contract

The exploration grid endpoint should accept persistent filter inputs, such as:

- `view_mode`
- `person_ids`
- `tag_paths`

The implementation should be designed so more advanced future filters can be
added without changing the architectural direction.

At minimum, the contract should explicitly allow future server-side filters for:

- location geometry constraints
- distance-based filters
- filename-based filters
- other full-dataset predicates

This task does not require all of those filters to be implemented now, but the
API contract and backend query flow must no longer assume client-side filtering
as the long-term model.

### Keep Bootstrap Lightweight

The bootstrap endpoint should return:

- resolved range
- available view modes
- visible person catalog
- visible tag catalog

The bootstrap payload must not include the full dense grid and must not include
per-day hover payloads.

Range resolution should remain derived-backed.
Person and tag catalogs may remain canonical in this task if that is still the
cleanest current source.

### Keep Day Context Bounded and Hover-Oriented

`GET /days/context` should remain a bounded range preload endpoint and should be
positioned as the hover/context channel, not the primary persistent filtering
channel.

This task should decide whether day-context data:

- continues to read canonical data temporarily, or
- moves to derived daily aggregates now

Either choice is acceptable for this task as long as it is explicit and
documented in the implementation notes and tests.

However, the endpoint must remain bounded-range oriented so the UI can preload
visible windows and serve hover interaction locally without one request per day.

### Update API Tests

Tests must cover the new contract split and the new layering expectations.

At minimum, add or update coverage for:

- empty bootstrap response shape
- empty derived grid response shape
- derived grid range resolution without canonical fallback
- persistent filter parameters being accepted by the grid endpoint
- bounded day-context loading remaining separate from grid activity loading

## Out of Scope

- no UI implementation changes beyond what is required to keep tests/builds
  coherent
- no introduction of every future advanced filter in this task
- no speculative GraphQL or query-language layer
- no requirement to move all catalogs into derived storage

## Acceptance Criteria

- bootstrap, grid, and day-context responsibilities are exposed through
  explicitly separated API contracts
- the grid endpoint returns only derived day activity fields needed for grid
  rendering
- persistent filters are modeled as server-side inputs to the grid endpoint
- the API no longer assumes client-side filtering over preloaded day summaries
  as the long-term filtering model
- range resolution for the grid remains derived-only
- tests cover the new contract boundaries and the lack of canonical grid
  fallback

## Notes

This task is about establishing the backend contract direction, not finishing
every future filter implementation.

The key correction is architectural:

- the browser should not own full-dataset persistent filtering logic
- the backend should own persistent filter evaluation
- the client should keep only the bounded hover-context preload responsibility

