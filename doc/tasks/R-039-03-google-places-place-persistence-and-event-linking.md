# R-039-03 - Google Places Place Persistence and Event Linking

## Goal

Persist resolved Google Places snapshots into the generic `place` cache and
link qualifying canonical events through `event_place` idempotently.

## Dependencies

- `R-039-01`
- `R-039-02`

## Scope

### Apply Refresh-Aware Place Upserts

Implement derive persistence behavior for three place states:

- missing cached place
- fresh cached place
- stale cached place

For each unique provider place id:

- insert a new `place` row when none exists
- leave the row unchanged when a fresh cached row already satisfies the request
- update the row and `lastupdate_at` when the cached row is stale and a fresh
  provider response is fetched

The staleness decision must come from configured refresh age, not from an
inlined constant in repository code.

### Persist Only the Selected Fields

Map the provider response into `place` using only:

- `source_id`
- `external_id`
- `display_name`
- `formatted_address`
- `latitude`
- `longitude`
- `lastupdate_at`

No raw response payload should be written to the database.

### Link Every Qualifying Event

After place resolution, ensure each qualifying canonical event is linked to the
resolved place row through `event_place`.

The link behavior must be deterministic and idempotent:

- insert the link when missing
- update `confidence` when the row exists but the confidence changed
- leave the row unchanged when both place and confidence already match

### Reconcile Conflicting Event Links for This Use Case

Because the current derive use case represents one resolved provider place per
qualifying event, the persistence behavior should not allow one event to keep an
old conflicting link from a previous run.

If an event currently links to a different place through this derive path, the
job should replace the link with the place resolved from the current
`googlePlaceId`.

### Return a Meaningful Persistence Summary

The persistence layer should return explicit counters at least for:

- inserted place count
- updated place count
- unchanged place count
- inserted event-place link count
- updated event-place link count
- unchanged event-place link count

These counters will later feed the derive progress summary and CLI output.

## Out of Scope

- no CLI progress formatting yet
- no OpenAPI or read-model changes yet
- no generic cleanup of all orphaned places

## Acceptance Criteria

- missing, fresh, and stale cached-place cases are handled deterministically
- stale places are refreshed according to configured age policy
- `place` writes persist only the selected relational fields
- qualifying events are linked through `event_place` without duplicate rows
- conflicting old event-to-place links are reconciled to the current resolved
  place
- persistence returns explicit counters for both place rows and event-place
  links

## Notes

For this series, the confidence signal is intentionally narrow:
`event_place.confidence` should reflect the canonical Google Maps candidate
probability when available, not a newly invented provider-side scoring model.
