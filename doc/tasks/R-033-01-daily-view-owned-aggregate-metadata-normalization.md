# R-033-01 - Daily-View-Owned Aggregate Metadata Normalization

## Goal

Normalize derived aggregate metadata by moving the `metadata` column out of
`daily_aggregate` and into `daily_view`.

Today `daily_aggregate.metadata` is duplicated across all aggregate rows that
point at the same `daily_view`. Once the `daily_view_id` is the same, the
metadata payload is effectively identical as well. That duplication is
unnecessary and should be removed.

This task should make `daily_view` the owner of that metadata and leave
`daily_aggregate` responsible only for day-varying derived measurements.

## Dependencies

- `R-031-02`
- `R-031-03`
- `R-032`

## Scope

This task is limited to the derived schema, the derive persistence path, and
the migration behavior needed to preserve existing data.

### Required Schema Direction

Reshape the derived schema so that:

- `daily_aggregate.metadata` is removed
- `daily_view` gains a `metadata` JSON column
- metadata is stored exactly once per reusable view definition

The intent is that:

- `daily_view` owns view-level metadata
- `daily_aggregate` keeps only per-day values such as counts, scores, and
  day-level summaries

### Required Persistence Direction

Update the derive write path so metadata is written through `daily_view`
instead of being repeated on every `daily_aggregate` row.

That includes adapting the derive job and any repository code involved in
resolving or creating `DailyView` rows so that:

- the view metadata is persisted when the view is created or updated
- `DailyAggregate` rows no longer attempt to write a metadata payload
- repeated derive runs remain deterministic and idempotent

The end state should not keep a redundant metadata copy on both tables.

### Required Migration Direction

Provide a schema migration that preserves existing metadata in both upgrade and
downgrade directions.

For the upgrade:

- add `daily_view.metadata`
- backfill it from existing `daily_aggregate.metadata`
- the backfill may take the payload from the first example row for each
  `daily_view_id`, because all rows for one view are expected to contain the
  same metadata
- remove `daily_aggregate.metadata`

For the downgrade:

- recreate `daily_aggregate.metadata`
- backfill it from the joined `daily_view.metadata`
- restore the legacy duplicated representation exactly enough for compatibility

The migration may rely on a direct `daily_aggregate` to `daily_view` join when
reconstructing the old shape.

### Read-Path Direction

Any read models or API-facing code that currently expects aggregate metadata
must be updated to read the normalized source if needed.

If no active read path currently uses that metadata, keep the normalization
localized and avoid speculative read-model expansion.

## Out of Scope

- no redesign of the meaning or content of the metadata payload itself
- no broader daily-view schema redesign beyond moving this column
- no new user-facing API contract unless required by an existing read path
- no attempt to normalize other day-level summary JSON columns in this task

## Acceptance Criteria

- `daily_aggregate` no longer contains a `metadata` column
- `daily_view` contains a `metadata` JSON column
- the derive job persists metadata through `daily_view`
- repeated derive runs remain deterministic and idempotent
- the upgrade migration backfills `daily_view.metadata` from existing
  `daily_aggregate` rows using one representative row per `daily_view_id`
- the downgrade migration restores `daily_aggregate.metadata` from
  `daily_view.metadata` via the table relationship
- tests cover the schema change and the adjusted derive persistence behavior

## Notes

This is a normalization task, not a product semantics change.

The important architectural correction is:

- view-invariant metadata belongs to `daily_view`
- day-varying measurements belong to `daily_aggregate`
