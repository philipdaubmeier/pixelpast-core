# R-047-03 - Global Person-Group Filter State and Shell Foundation

## Goal

Introduce `PersonGroup` as a shared app-level filter dimension that survives
main-view switches and can be consumed by both `Photo Album` and `Social
Graph`.

## Dependencies

- `R-024-02`
- `R-035-01`
- `R-047-01`

## Scope

### Add Shared Person-Group Filter State

Extend the global filter model with selected `person_group_ids`.

This state should:

- be explicit in app-level client state
- survive switching between main views
- participate in URL or bootstrap persistence if the current app architecture
  already does that for other global filters

### Add A Reusable Person-Group Filter Control

Introduce one shared top-bar filter control for person groups.

The control should:

- list persisted groups by name
- expose group color when available
- support multi-select
- remain visible in both `Photo Album` and `Social Graph`

This is a global filter entry point, not an album-local side panel.

### Keep Existing Filters Coherent

This task should define how the new filter composes with existing global
filters rather than bypassing them.

Direction:

- person-group filter is additive with the existing filter model
- view-specific transports receive the full current filter state
- no hidden fallback state should live inside album or social-graph components

## Out of Scope

- no view-specific API filtering behavior yet
- no album chip rendering yet
- no social-graph node recoloring yet

## Acceptance Criteria

- app state supports selected `person_group_ids` as a global filter dimension
- the shell exposes a shared person-group filter control
- the selected person-group filter survives main-view switches
- the client transport layer can forward selected `person_group_ids` to view
  endpoints that later choose to support them

## Notes

This task exists to prevent duplicated filter logic.
If album and social graph each invent their own person-group selection state,
the series has already drifted off course.
