# R-031-01 - Demo View Renaming and UI View Color Decoupling

## Goal

Exploration-demo cleanup in two parts:

- rename the demo-facing exploration views from activity-themed placeholder
  names to source-oriented names
- remove the UI's hard-coded semantic color coupling to specific server view ids

This task is the first subtask to create a clear baseline for later work on
dynamic server-defined daily views.

## Dependencies

- `R-014`
- `R-016`
- `R-017`
- `R-024-01`
- `R-024-02`

## Scope

The task consists of the following changes:

- the demo exploration/bootstrap payload exposes source-oriented example
  views instead of placeholder names
- the demo provider internals use the same renamed concepts consistently
- the UI no longer assigns colors based on specific view ids such as
  `activity`, `travel`, or other named modes
- the UI instead assigns colors positionally from the bootstrap-provided
  `view_modes` list
- available CSS color tokens are generic and numbered, for example
  `--pp-grid-viewcolor1`, `--pp-grid-viewcolor2`, and so on
- when the server provides more views than there are configured color tokens,
  the UI reuses colors cyclically via modulo behavior
- the client no longer relies on a fixed compile-time enum of known view ids
- if a persisted or URL-derived `viewMode` is not present in the current
  bootstrap response, the UI falls back to the first server-provided view

### Design Direction

This task establishes an important boundary:

- the server owns which views exist
- the client owns only presentation mechanics such as assigning reusable colors
  to those views

That direction should be preserved by follow-up server work. The UI must not
reintroduce semantic branching on specific server view ids unless that behavior
is explicitly justified and documented.

## Out of Scope

- no server-side schema changes yet
- no changes to how derived views are stored in the database yet
- no automatic server-side discovery of all daily aggregate variants yet
- no redesign of the filter model beyond removing the hard-coded client view id
  list

## Acceptance Criteria

- client no longer depends on a fixed enum of known view ids
- server side demo views are renamed

## Notes

This is a bridge task between the demo-oriented bootstrap work and the next
server-side step: introducing a persistent daily-view catalog in the derived
schema so the bootstrap API can become fully database-driven.
