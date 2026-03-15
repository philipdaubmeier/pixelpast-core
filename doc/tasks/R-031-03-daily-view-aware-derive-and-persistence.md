# R-031-03 - Daily View Aware Derive and Persistence

## Goal

Adapt derive and persistence flows so `DailyAggregate` rows are written against
`DailyView` records instead of being identified only by inline string columns.

## Dependencies

- `R-023-02`
- `R-031-02`
- `R-031`

## Scope

This task should update the derive pipeline and repository layer so the new
`daily_view` catalog becomes operational.

### Repository Direction

Introduce the persistence support needed to:

- resolve or create the appropriate `DailyView`
- look up a `DailyView` by `aggregate_scope` and nullable `source_type`
- write `DailyAggregate` rows that reference the resolved `DailyView`

The repository boundary should continue to own all direct database interaction.

### Derive Job Direction

The derive job should no longer treat `aggregate_scope` and `source_type` as
the full definition of a view row. Instead it should:

- resolve the target `DailyView`
- write aggregate rows against that view identity
- populate or preserve the corresponding label and description metadata

The label and description source can initially be deterministic backend-owned
logic if needed, but they must end up persisted in `daily_view` rather than
reassembled only at API time.

### Behavioral Direction

After this task:

- repeated derive runs must reuse the same `DailyView` rows
- `DailyAggregate` rows must be associated with stable `DailyView` identities
- new derived views can be added without reshaping the bootstrap API contract

## Out of Scope

- no bootstrap API switch yet
- no UI changes
- no general user-managed custom-view authoring workflow

## Acceptance Criteria

- derive and repository code can resolve or create `DailyView` rows
- derived aggregates are persisted via `daily_view_id`
- repeated derive runs reuse existing matching `DailyView` definitions
- label and description metadata are stored in `daily_view`

## Notes

This task is where the new schema becomes live. The follow-up bootstrap task
should then become a read-path refactor instead of inventing metadata on the
fly.
