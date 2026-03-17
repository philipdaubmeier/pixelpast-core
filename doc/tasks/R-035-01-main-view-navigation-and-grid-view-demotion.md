# R-035-01 - Main-View Navigation Foundation and Grid-View Demotion

## Goal

Refactor the UI shell so the application has an explicit app-level main-view
concept above the existing timeline-specific view selection.

Today the top bar mixes one concern:

- choosing the timeline coloring mode

The next state should separate two concerns:

- choosing the active main view of the product
- choosing the active grid view within `Day Grid`

This first task introduces that structural split while keeping `Day Grid` as
the only implemented main view for now.

## Dependencies

- `R-024-02`
- `R-031-04`
- `R-034-05`

## Scope

### State and URL Direction

Introduce an explicit persistent `mainView` state in the UI shell and URL
model.

For this task:

- `mainView` exists and defaults to `day_grid`
- `day_grid` is the only active main-view implementation
- the existing timeline `viewMode` concept is renamed in the UI architecture to
  `gridView`

The timeline backend request contract may continue to use `view_mode`
internally for now. The important correction here is the UI and shell
distinction:

- app shell owns `mainView`
- timeline view owns `gridView`

### Top-Bar Direction

Restructure the top bar into two rows:

- row 1: logo, main-view navigation area, and persistent global filters
- row 2: day-grid-only `grid views`

The row-2 controls must read as subordinate to the main-view navigation, for
example through smaller size, a quieter color treatment, or other clearly
secondary styling.

### Behavioral Direction

Persistent filters such as persons, tags, and future date range controls remain
visible in the top bar regardless of the active main view.

This task does not yet add a working `Social Graph` button, data query, or
renderer. It only prepares the shell and terminology so that later work does
not overload one ambiguous `viewMode` concept.

## Out of Scope

- no social-graph data fetching yet
- no new backend API work
- no graph-specific UI states yet
- no change to the current day-grid rendering behavior

## Acceptance Criteria

- the UI shell has a persistent `mainView` concept with `day_grid` as default
- the top bar is structurally split into a main row and a day-grid-specific
  secondary row
- current timeline view options are presented as `grid views`, not as the
  product's top-level navigation
- global filters remain visible independent of the secondary row
- current day-grid behavior remains otherwise unchanged

## Notes

This task is mostly about naming, state ownership, and shell structure. That
correction is necessary before the social graph is added, otherwise the next
feature will inherit an ambiguous and brittle navigation model.
