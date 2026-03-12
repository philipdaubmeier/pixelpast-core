# R-014 - Exploration Bootstrap API v1

## Goal

Add a UI-facing exploration bootstrap endpoint that provides the current React
shell with the data it actually needs.

This should sit above the existing low-level heatmap endpoint instead of
overloading it with UI-shell concerns.

---

## Scope

Implement a new read-oriented endpoint:

- `GET /exploration`

The response should include:

- `range`
- `view_modes`
- `persons`
- `tags`
- `days`

`days` should be dense across the resolved date window and expose:

- `date`
- `event_count`
- `asset_count`
- `activity_score`
- `color_value`
- `has_data`
- `person_ids`
- `tag_paths`

Range behavior:

- use explicit `start` and `end` when provided
- otherwise resolve the available timeline and pad it to full calendar years
- if no real data exists, return the current calendar year as an empty dense
  grid so the UI can still render its primary surface

View mode behavior:

- backend owns the available view modes
- preserve the current four UI modes for v1
- port the current frontend view-mode heuristics to Python so the initial live
  behavior remains familiar

Keep the existing endpoints:

- `GET /heatmap`
- `GET /days/{date}`

They remain available as lower-level timeline APIs.

---

## Out of Scope

- no day-hover context endpoint in this task
- no UI implementation
- no day detail redesign
- no speculative query language for complex filters
- no removal of the existing low-level timeline endpoints

---

## Acceptance Criteria

- `GET /exploration` returns an explicit schema rather than ORM models
- the endpoint works with empty and populated datasets
- the response includes dense days across the resolved range, including empty
  days
- all four current view modes are returned by the backend
- backend color values match the current frontend heuristics for the same input
  data
- persons and tags required by the current shell are included in the bootstrap
  response
- endpoint behavior is covered by integration tests

---

## Notes

This task creates a UI-facing projection endpoint.
It should not weaken the existing read-oriented heatmap and day-detail APIs.
Keep the contract explicit and stable.
