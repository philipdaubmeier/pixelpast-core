# R-007 - Heatmap and Day API v1

## Goal

Expose the first read-oriented API endpoints that directly support temporal
exploration.

This task should serve the product goal more directly than a generic combined
timeline feed.

---

## Scope

Implement:

- `GET /heatmap?start=...&end=...`
- `GET /days/{date}`

`GET /heatmap` should return day-level data derived from `DailyAggregate`.

`GET /days/{date}` should return a read model for one day that combines:

- `Event.timestamp_start`
- `Asset.timestamp`

The day detail response should be time-ordered and use explicit Pydantic
schemas.

---

## Out of Scope

- No authentication
- No tag/person filters yet
- No pagination beyond a simple pragmatic limit if needed
- No UI implementation
- No ORM models returned directly

---

## Acceptance Criteria

- heatmap endpoint works with empty and populated datasets
- day detail endpoint works with events only, assets only and mixed data
- responses use explicit API schemas
- endpoint behavior is covered by integration tests

---

## Notes

Prefer read-oriented projection models over leaking canonical persistence
structures.
This task intentionally prioritizes heatmap and day exploration over a generic
timeline endpoint.
