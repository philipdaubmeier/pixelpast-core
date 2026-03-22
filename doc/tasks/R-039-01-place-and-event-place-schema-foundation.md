# R-039-01 - Place and Event-Place Schema Foundation

## Goal

Add the derived relational schema and repository boundaries required for reusable
place caching and event-to-place linking.

## Dependencies

- `R-038-06`

## Scope

### Add the `place` Table

Introduce a new `place` table with exactly these fields:

- `id`
- `source_id`
- `external_id`
- `display_name`
- `formatted_address`
- `latitude`
- `longitude`
- `lastupdate_at`

The table should enforce deterministic provider-scoped identity through a
uniqueness rule on:

- `(source_id, external_id)`

Add practical indexes for:

- provider-scoped lookup by external id
- refresh-age lookup by `lastupdate_at`
- future geographic filtering by latitude and longitude

### Add the `event_place` Table

Introduce a new `event_place` association table with:

- `event_id`
- `place_id`
- `confidence`

The natural identity for this series should be:

- one row per `(event_id, place_id)`

`confidence` should be nullable because some canonical events may expose a place
id without a usable confidence signal.

### Keep the Tables Minimal

Do not add `metadata_json` or any provider-specific JSON payload fields to
either table in this task.

The schema goal is a tight relational cache for selected place detail, not a
remote payload archive.

### Represent the Provider Through Existing Source Persistence

This task should make explicit that `place.source_id` points to the existing
canonical `source` table rather than introducing a dedicated provider table.

The derive implementation will later create or reuse a deterministic source row
for Google Places API provenance.

### Add Repository Support

Introduce repository boundaries for the new derived tables.

At minimum, the persistence layer should support:

- fetch one place by `(source_id, external_id)`
- upsert one place row
- fetch existing event-place links for a deterministic event or place set
- create or update one event-place link idempotently

The repository contracts should be shaped for derive use and testability rather
than for a generic ORM pass-through.

## Out of Scope

- no Google Places API client yet
- no derive job wiring yet
- no CLI changes yet
- no API read endpoint changes yet

## Acceptance Criteria

- the derived schema contains a new `place` table with the requested minimal
  field set
- the derived schema contains a new `event_place` table with nullable
  `confidence`
- `place` enforces provider-scoped uniqueness through `(source_id, external_id)`
- repository boundaries exist for deterministic place upsert and event-place
  link persistence
- no metadata JSON columns are introduced

## Notes

This task intentionally keeps the schema provider-agnostic even though the first
writer will be the Google Places derive job.
