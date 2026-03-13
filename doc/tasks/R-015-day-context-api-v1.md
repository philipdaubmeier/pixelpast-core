# R-015 - Day Context Range API v1

## Goal

Add a dedicated hover-context preload endpoint for the right-side UI panels.

The current `GET /days/{date}` endpoint is intentionally timeline-oriented and
should remain focused on future day-detail storytelling rather than hover panel
bootstrap.

A single-day hover endpoint is not sufficient for the calendar grid UI.
Requesting one day per mouse move would create avoidable latency and could
generate large request bursts while the pointer moves across many small pixels.

The API should instead allow the UI to preload hover context for a bounded date
range and cache it locally.

---

## Scope

Implement:

- `GET /days/context?start=<date>&end=<date>`

The response should include:

- `range`
- `days`

`days` should be dense across the requested UTC date window and include, for
each day:

- `date`
- `persons`
- `tags`
- `map_points`
- `summary_counts`

Context behavior:

- aggregate results independently per UTC day within the requested range
- `persons` are the union of event-linked and asset-linked people for each UTC
  day
- `tags` are the union of event-linked and asset-linked tags for each UTC day
- `summary_counts` should expose at least:
  - events
  - assets
  - places
- empty days must still be returned so the UI can cache a complete visible
  window without extra probing requests

Map behavior:

- move away from mock screen coordinates
- `map_points` should expose real coordinates for each day:
  - `id`
  - `label`
  - `latitude`
  - `longitude`
- provide a deterministic label fallback when no better label exists

Range behavior:

- require explicit `start` and `end`
- reject inverted or invalid ranges
- enforce a configurable maximum number of requested days
- return a clear API error when the requested range exceeds that limit

Preferred v1 direction:

- do not add pagination yet
- let the UI request the currently visible window and preload it into a local
  cache
- if the UI needs a larger surface later, it can issue multiple bounded range
  requests

Keep:

- `GET /days/{date}`

unchanged as the future day-detail timeline endpoint.

---

## Out of Scope

- no day detail UI
- no single-request unbounded hover preload
- no server-driven pagination in v1
- no map library integration
- no backend-driven screen-space map layout
- no overhaul of the existing day-detail endpoint

---

## Acceptance Criteria

- `GET /days/context?start=<date>&end=<date>` returns a dense per-day context
  list for the requested UTC range
- the endpoint works for empty ranges, event-only days, asset-only days, and
  mixed linked data
- person and tag results include associations from both events and assets for
  each returned day
- map points expose latitude and longitude, not UI-specific `x` and `y`
- unlabeled coordinate points still produce stable labels
- requests beyond the configured maximum day count fail with an explicit API
  error
- `GET /days/{date}` remains unchanged
- endpoint behavior is covered by integration tests, including range-limit
  failure cases

---

## Notes

This task creates a dedicated hover-context projection for range preload.
Keep it lightweight and UI-oriented.
Do not collapse it into the future day-detail story endpoint.

The v1 optimization strategy is bounded preloading, not transport pagination.
That is the simpler contract and is sufficient for the current hover and
visible-range caching problem.
