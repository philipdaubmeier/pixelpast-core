# R-023-01 - Daily Aggregate Schema v2

## Goal

Redesign the `DailyAggregate` derived schema so it can represent connector-aware
per-day summaries instead of only global event and media counts.

The current model is too narrow for the intended exploration behavior. It does
not distinguish connector/source type and it does not persist day-level
summaries for keywords, persons, or locations. This task should define the new
derived schema contract first, before derive-job or API changes are made.

## Dependencies

- `R-006`

## Scope

### Introduce Connector-Aware Daily Aggregate Identity

Revise the `DailyAggregate` identity so a single UTC day can hold multiple
derived aggregate rows partitioned by connector or source type.

The revised model must make it possible to represent daily summaries for inputs
such as:

- photos
- calendar
- spotify or music history
- future ingestion connectors

The exact field name may vary, but the semantics must be explicit. Examples of
acceptable concepts are:

- `source_type`
- `connector_type`
- `aggregate_scope`

This field must be stable, queryable, and suitable for indexing.

### Add Derived Payloads for Daily Semantic Summaries

Extend the derived model so a day aggregate can carry summarized metadata needed
for grid-level and connector-level exploration.

At minimum, the derived schema must support:

- aggregated tag or keyword summaries for the day
- aggregated person summaries for the day
- aggregated location summaries for the day

The representation may use explicit columns, structured JSON payloads, or a
hybrid design, but it must remain deterministic and queryable enough for the
API layer to consume without falling back to canonical joins.

### Clarify Overall vs Connector-Scoped Aggregates

The schema design must state how "all sources combined" is represented relative
to connector-scoped rows.

The design must choose one of these approaches explicitly:

- store both overall and connector-scoped rows
- store only connector-scoped rows and define a separate derived rollup path

Either choice is acceptable, but the task must not leave the distinction
implicit.

### Review Derived Counts and Activity Semantics

Reassess the meaning of existing fields such as:

- `total_events`
- `media_count`
- `activity_score`

The schema revision should define whether these fields remain global, become
connector-scoped, or require additional count columns to stay semantically
clear in the new model.

### Define Migration Expectations

This task includes the schema and migration design needed to move from the
current daily aggregate table to the new structure.

The migration plan must ensure:

- deterministic upgrade behavior
- clear primary key / uniqueness rules
- indexes aligned with date and connector-aware queries

## Out of Scope

- no derive job implementation changes
- no exploration API logic changes
- no UI changes
- no new canonical tables or canonical-model restructuring

## Acceptance Criteria

- the derived schema can represent multiple aggregate rows for the same date
  across connector/source types
- the schema contract explicitly defines how connector identity is stored
- the schema can persist daily summaries for tags, persons, and locations
- the schema explicitly defines how overall vs connector-scoped aggregation is
  represented
- the migration and indexing requirements are documented clearly enough for
  implementation

## Notes

This task should prefer explicit semantics over compactness. A slightly more
verbose derived schema is acceptable if it avoids ambiguous API behavior later.
