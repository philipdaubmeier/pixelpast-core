# R-028-01 - Daily Aggregate Job Responsibility Split

## Goal

Split the current `analytics/daily_aggregate.py` implementation into a thin job
orchestration shell plus a small set of explicit collaborators, analogous to
the responsibility cleanup done for ingest workers in `R-022-xx`.

The current derive job mixes several concerns in one place:

- canonical input loading
- date-range validation
- aggregate-state construction
- summary payload building
- persistence mode selection (`replace_all` vs `replace_range`)
- result assembly

That is already enough complexity to justify a modest internal split, but not a
generic derive framework.

## Dependencies

- `R-023-02`

## Scope

### Introduce Explicit Daily Aggregate Collaborators

Refactor the daily aggregate implementation into clearly named responsibilities.

At minimum, make the following concerns explicit:

- canonical input loading
- snapshot construction from canonical inputs
- derived-row persistence
- top-level job orchestration

Acceptable end states include:

- a small `analytics/daily_aggregate/` package
- a thin facade file delegating to a few local collaborators

Do not force a package split if two or three extracted collaborators keep the
code clearer.

### Keep the Job API Stable

The public daily aggregate job entrypoint should remain operationally stable.

The external call shape should continue to be compatible with the current
derive entrypoint:

- `DailyAggregateJob().run(...)`
- `DailyAggregateJobResult`

### Preserve the Pure Aggregation Core

The logic that builds deterministic aggregate rows from canonical input data
should remain easy to unit test without database setup.

The refactoring should make it more obvious which code is:

- pure aggregation logic
- persistence-facing orchestration

### Avoid a Premature Base Class or Runner

Do not introduce:

- a generic derive runner
- a template hierarchy for all future derive jobs
- cross-job abstractions that only the daily aggregate job uses today

If a later second derive job proves common orchestration, that can be extracted
after this task. Not before.

## Out of Scope

- no derive-run persistence yet
- no CLI progress output yet
- no schema redesign beyond what the current daily aggregate job already needs

## Acceptance Criteria

- `analytics/daily_aggregate.py` no longer acts as the home of every derive-job
  responsibility
- the daily aggregate job becomes a thin composition root or orchestration shell
- canonical input loading, snapshot building, and persistence decisions are
  visually distinct and independently testable
- daily aggregate behavior remains deterministic and idempotent
- no generic derive-job framework is introduced

## Notes

This task is the derive-side equivalent of making the photo ingest service stop
being an implementation bucket. The right end state is clarity, not machinery.
