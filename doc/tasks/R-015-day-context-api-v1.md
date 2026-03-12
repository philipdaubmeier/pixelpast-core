# R-015 - Day Context API v1

## Goal

Add a dedicated hover-context endpoint for the right-side UI panels.

The current `GET /days/{date}` endpoint is intentionally timeline-oriented and
should remain focused on future day-detail storytelling rather than hover panel
bootstrap.

---

## Scope

Implement:

- `GET /days/{date}/context`

The response should include:

- `date`
- `persons`
- `tags`
- `map_points`
- `summary_counts`

Context behavior:

- `persons` are the union of event-linked and asset-linked people for that UTC
  day
- `tags` are the union of event-linked and asset-linked tags for that UTC day
- `summary_counts` should expose at least:
  - events
  - assets
  - places

Map behavior:

- move away from mock screen coordinates
- `map_points` should expose real coordinates:
  - `id`
  - `label`
  - `latitude`
  - `longitude`
- provide a deterministic label fallback when no better label exists

Keep:

- `GET /days/{date}`

unchanged as the future day-detail timeline endpoint.

---

## Out of Scope

- no day detail UI
- no month or range hover behavior
- no map library integration
- no backend-driven screen-space map layout
- no overhaul of the existing day-detail endpoint

---

## Acceptance Criteria

- `GET /days/{date}/context` works for empty days
- the endpoint works for events only, assets only, and mixed linked data
- person and tag results include associations from both events and assets
- map points expose latitude and longitude, not UI-specific `x` and `y`
- unlabeled coordinate points still produce stable labels
- `GET /days/{date}` remains unchanged
- endpoint behavior is covered by integration tests

---

## Notes

This task creates a dedicated hover-context projection.
Keep it lightweight and UI-oriented.
Do not collapse it into the future day-detail story endpoint.
