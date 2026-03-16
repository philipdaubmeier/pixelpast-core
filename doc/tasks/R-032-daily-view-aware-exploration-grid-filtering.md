# R-032 - Daily-View-Aware Exploration Grid Filtering

## Goal

Make the exploration grid backend actually load and return the `daily_aggregate`
rows that belong to the requested `daily_view`.

Today the backend validates `view_mode` against the persisted `daily_view`
catalog, but the grid read path still loads only the overall aggregate rows.
As a result, the API returns the same `daily_aggregate` data regardless of
which view was requested.

This task closes that gap.

## Dependencies

- `R-024-01`
- `R-031-02`
- `R-031-03`
- `R-031-04`

## Scope

This task is limited to the backend exploration-grid read path.

### Required Read-Path Direction

The exploration grid provider should no longer treat `view_mode` as a
validation-only input.

Instead, the backend should:

- resolve the requested API `view_mode` to one concrete persisted `DailyView`
- load only the `DailyAggregate` rows for that view in the requested date range
- build the dense grid from those selected rows

The selected view must be the source of truth for which derived day rows are
visible in the grid.

### Repository Direction

Introduce or adapt repository read behavior so the grid path can query
aggregates for one resolved `DailyView`.

The repository behavior should make the following operations explicit:

- resolve a `DailyView` from the API-facing `view_mode` identifier
- list `DailyAggregate` rows for that view and date range

The end state should not rely on loading all source-scoped rows and filtering
them indirectly in provider code.

### Provider Direction

The exploration provider should compose the grid from the resolved selected
view, not from the overall fallback path.

That means:

- `view_mode=activity` loads the overall `DailyView`
- `view_mode=<source_type>` loads that source-scoped `DailyView`
- the dense `aggregate_map` used by the grid is built only from rows belonging
  to the selected view

### Behavioral Direction

The grid response must change when different daily views contain different
derived values for the same day.

For example:

- one day may have an overall aggregate row and a calendar-scoped row
- requesting `activity` should use the overall row
- requesting `calendar` should use the calendar row
- requesting another valid view with no row for that day should return the
  empty day payload for that day

### Test Direction

Add or update backend tests so the actual view-specific row selection is
verified.

At minimum, coverage should include:

- two different `DailyView` rows with aggregates on the same date
- different grid results for different `view_mode` values over that date
- empty-day behavior when the selected view has no aggregate row for a date
- rejection of unknown `view_mode` values still resolving against the
  `daily_view` catalog

The existing filter tests should no longer pass purely because `view_mode`
changes color heuristics while the underlying aggregate row stays the same.

## Out of Scope

- no redesign of the grid response contract
- no user-authored custom daily-view formulas
- no change yet to make color semantics fully data-driven
- no expansion of person, tag, location, or filename filtering beyond what the
  current endpoint already models
- no schema redesign unless a narrowly scoped persistence adjustment is strictly
  necessary for the read path

## Acceptance Criteria

- the exploration grid backend resolves the requested `view_mode` to a concrete
  persisted `DailyView`
- the grid loads only `DailyAggregate` rows associated with that selected view
- different requested views can produce different day payloads for the same date
- requesting a valid view that has no aggregate row for a day yields the normal
  empty grid-day payload for that day
- tests explicitly prove that the backend no longer always returns overall
  aggregates regardless of requested view

## Notes

This task is intentionally about correctness of the derived read path, not
about introducing arbitrary dynamic view formulas.

The architectural correction is narrow but important:

- `daily_view` must not stop at bootstrap metadata and request validation
- it must also drive which `daily_aggregate` rows the exploration grid reads
