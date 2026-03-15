# R-031 - Dynamic Daily View Catalog and Bootstrap API

## Goal

Move exploration view definitions out of hard-coded backend constants and into
the derived data model so the bootstrap API can load the available view list
from the database.

Today the backend still defines the exploration `view_modes` catalog in code.
That is incompatible with the desired direction where daily aggregate views are
first-class derived entities with explicit metadata.

This task series should introduce a `daily_view` catalog table and make
`daily_aggregate` rows reference that catalog through a foreign key. The
exploration bootstrap API should then read the view list from `daily_view`
instead of assembling it from hard-coded definitions.

## Dependencies

- `R-023-01`
- `R-023-02`
- `R-024-01`
- `R-031-01`

## Scope

This task series should restructure the derived layer around an explicit daily
view catalog.

### Required Schema Direction

The current derived representation is not sufficient:

- `daily_aggregate.aggregate_scope`
- `daily_aggregate.source_type`

Those two string columns must no longer be the complete view identity model.
Instead, introduce a dedicated `daily_view` table that owns view metadata and
identity.

The new `daily_view` table should contain at least:

- id
- aggregate_scope
- source_type, nullable
- label
- description

The `daily_aggregate` table should then reference `daily_view` via foreign key
instead of carrying only the existing pair of string columns as its effective
view definition.

### Required Domain Direction

The domain model should make the daily view catalog explicit:

- `DailyAggregate` represents one day-level derived measurement for one view
- `DailyView` represents the reusable definition of that view

The relationship must be queryable and deterministic:

- many `DailyAggregate` rows may point at one `DailyView`
- bootstrap view metadata comes from `DailyView`
- aggregate rows do not need to duplicate label and description text

### Required API Direction

After this task series:

- the bootstrap API reads the view list from the database
- the order exposed to the UI must be stable and deterministic
- the API contract shape can remain the same
- hard-coded backend view definitions should no longer be the source of truth

## Subtasks

- `R-031-01`
  - rename demo-facing example views and decouple UI colors from semantic view
    ids
- `R-031-03`
  - introduce the `DailyView` domain and schema foundation
- `R-031-04`
  - adapt derive and persistence paths so `DailyAggregate` rows target
    `DailyView`
- `R-031-05`
  - switch bootstrap view loading from hard-coded definitions to the
    `daily_view` catalog

## Out of Scope

- no change yet to make the day grid itself dynamically compose arbitrary view
  formulas from user-configurable definitions
- no user-editable CRUD UI for daily views
- no change yet to load all other exploration catalogs from derived data
- no connector-specific business logic beyond what is required to map derived
  rows to `DailyView`

## Acceptance Criteria

- a documented task series exists for moving exploration view definitions into
  the database
- the series explicitly requires a new `daily_view` table with label and
  description fields
- the series explicitly requires `daily_aggregate` rows to reference
  `daily_view` by foreign key
- the series explicitly states that bootstrap view metadata must be read from
  the database instead of hard-coded backend constants

## Notes

This series is the server-side counterpart to `R-031-01`. The client is now
prepared to consume arbitrary server-defined views and assign colors
positionally. The backend should now make those views real derived entities.
