# R-031-02 - Daily View Domain and Schema Foundation

## Goal

Introduce the new `DailyView` concept into the derived/domain and persistence
layers and reshape the database schema so `daily_aggregate` rows reference that
catalog explicitly.

## Dependencies

- `R-023-01`
- `R-031`

## Scope

This task is the schema and model foundation for database-driven exploration
views.

### Domain Model Work

Add an explicit `DailyView` concept in the appropriate derived/domain boundary.
The model should represent:

- aggregate scope
- optional source type
- human-readable label
- human-readable description

The model should be designed as reusable view metadata, not as a denormalized
copy embedded inside each aggregate row.

### Persistence Work

Revise the persistence schema as follows:

- create a new `daily_view` table
- add a foreign key from `daily_aggregate` to `daily_view`
- migrate existing effective view identities into `daily_view`
- preserve the ability to distinguish overall vs scoped daily views through
  `aggregate_scope`
- preserve the ability to represent source-type-scoped views with nullable
  `source_type`

The final schema should make it possible to query:

- all defined daily views
- one daily view by scope plus source type identity
- all daily aggregates for one daily view

### Migration Direction

The migration should explicitly handle existing rows in SQLite:

- existing aggregate rows must be backfilled to matching `daily_view` entries
- no aggregate rows should remain orphaned
- the migration path should be deterministic and idempotent

## Out of Scope

- no bootstrap API changes yet
- no derive-job population changes beyond what is necessary to keep persistence
  valid during migration
- no UI changes

## Acceptance Criteria

- a new `daily_view` table exists with `aggregate_scope`, nullable
  `source_type`, `label`, and `description`
- `daily_aggregate` references `daily_view` by foreign key
- the domain/persistence model expresses `DailyView` as a first-class concept
- the migration plan explicitly covers existing SQLite rows

## Notes

This task should keep the existing derived layering explicit. `DailyView` is
metadata about a reusable derived projection, not a replacement for
`DailyAggregate` itself.
