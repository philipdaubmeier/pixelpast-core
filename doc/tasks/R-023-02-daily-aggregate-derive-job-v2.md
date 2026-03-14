# R-023-02 - Daily Aggregate Derive Job v2

## Goal

Update the daily aggregate derive job so it populates the revised connector-aware
daily aggregate schema introduced in `R-023-01`.

The job must stop thinking in terms of a single coarse day row and instead build
deterministic per-day derived summaries for each supported connector/source
type, plus any required overall rollups defined by the schema task.

## Dependencies

- `R-023-01`

## Scope

### Build Connector-Scoped Day Aggregates

Revise the derive job so it groups canonical input data by:

- UTC day
- connector or source type

The resulting derivation must produce one or more daily aggregate rows per day
according to the schema design from `R-023-01`.

### Populate Daily Semantic Summaries

The derive job must fill the new derived summary payloads for each day aggregate.

At minimum, it must compute and persist:

- aggregated tag or keyword summaries
- aggregated person summaries
- aggregated location summaries

The job should define deterministic summarization rules for these payloads, for
example:

- deduplication rules
- ordering rules
- truncation or top-N rules if needed
- handling of empty values and partial metadata

### Preserve Determinism and Idempotency

The updated job must remain:

- idempotent
- deterministic
- safe for full rebuilds
- safe for bounded date-range rebuilds if the job continues to support them

Connector-aware aggregation must not introduce nondeterministic ordering or
unstable payload shapes.

### Clarify Canonical Input Mapping

The job must define how canonical entities map into connector-aware daily
aggregates.

This includes:

- how assets and events contribute to a day aggregate
- how the connector/source identity is resolved
- how mixed-source days are represented
- how days with missing semantic metadata still receive valid aggregates

### Update Tests for the New Derived Contract

The derive layer test plan must be expanded to cover the revised model.

At minimum, tests should cover:

- multiple connector types on the same day
- days with only assets
- days with only events
- days with tags but no persons
- days with persons but no tags
- days with locations
- repeated runs producing the same derived rows

## Out of Scope

- no API adaptation work
- no UI changes
- no canonical ingest pipeline redesign beyond what is needed as job input

## Acceptance Criteria

- the derive job populates connector-aware daily aggregate rows according to the
  schema defined in `R-023-01`
- each aggregate row includes the required derived summaries for tags, persons,
  and locations
- the job remains deterministic and idempotent
- the derive job behavior for mixed-source days is explicitly defined
- automated tests cover connector-aware aggregation and semantic summary
  population

## Notes

This task is about derived data construction, not about changing where person
or tag catalogs come from in the UI. Its job is to make the derived layer rich
enough that the grid no longer depends on canonical fallback logic.
