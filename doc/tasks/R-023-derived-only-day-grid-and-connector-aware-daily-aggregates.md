# R-023 - Derived-Only Day Grid and Connector-Aware Daily Aggregates

## Goal

Shift the exploration day grid to a strictly derived-data projection while
keeping the UI's person and tag catalogs sourced from the canonical model.

Today the exploration bootstrap path can fall back to canonical events and
assets when daily aggregate rows are missing. That makes the grid visible
immediately after ingest even when no derive job has been executed yet. This
task series should remove that behavior and establish `DailyAggregate` as the
authoritative source for all grid-facing day cells.

At the same time, the derived schema must be expanded so it can represent a
connector-aware day summary instead of only coarse counts. The revised model
must support aggregated daily metadata such as:

- connector / source type
- daily keyword or tag summaries
- daily person summaries
- daily location summaries

The result should be a clean separation:

- canonical model remains the source of truth for raw timeline entities and
  reusable person/tag catalogs
- derived model becomes the source of truth for day-grid rendering and
  connector-scoped daily projections

## Dependencies

- `R-006`
- `R-014`
- `R-015`

## Scope

This task series is split into three implementation tasks:

- `R-023-01`
  - revise the derived schema for connector-aware daily aggregates
- `R-023-02`
  - update the daily aggregate derivation job to populate the revised model
- `R-023-03`
  - change API exploration/grid behavior to rely on derived rows only

### Target Behavioral Change

After this task series:

- running `ingest photos` alone must not make day-grid cells appear unless the
  corresponding derive job has populated daily aggregates
- person and tag catalogs in the UI may still be loaded from canonical
  associations
- the exploration/day-grid projection must no longer synthesize counts from raw
  canonical assets or events when derived rows are absent

### Design Direction

The revised derived layer should support one or more daily aggregate rows per
date, partitioned by connector or source type. The exact physical schema may
vary, but the model must make connector-aware projections explicit and
queryable.

This means the system should be able to represent, for one calendar day:

- an overall derived day summary
- one or more connector-scoped derived day summaries

If the final design uses only connector-scoped rows and computes an overall
rollup separately, that is acceptable as long as the contract remains explicit
and deterministic.

## Out of Scope

- no connector business-logic changes beyond what is required to support the
  revised derive job inputs
- no UI redesign of filters, panels, or interaction model
- no migration of all hover or detail context to derived data unless explicitly
  required by a subtask
- no new inferred analytics beyond the expanded daily summary payloads

## Acceptance Criteria

- a documented task series exists for schema, derive job, and API adaptation
- the series explicitly states that the day grid must be derived-only
- the series explicitly states that person and tag catalogs remain canonical
- the series explicitly requires connector-aware daily aggregate modeling
- the series explicitly requires aggregated daily metadata for tags, persons,
  and locations in the derived layer

## Notes

The main architectural correction is to remove the current ambiguity where the
exploration bootstrap endpoint mixes canonical fallback logic with derived day
state. The day grid should reflect the `Raw -> Canonical -> Derived` layering
strictly.
