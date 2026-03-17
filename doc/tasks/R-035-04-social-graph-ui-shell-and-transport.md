# R-035-04 - Social Graph UI Shell and Transport

## Goal

Add the `Social Graph` main view to the UI shell, wire it to the new API
endpoint, and introduce a dedicated view scaffold before the force-directed
visualization itself is implemented.

## Dependencies

- `R-035-01`
- `R-035-03`

## Scope

### Main-View Navigation Direction

Extend the shell from one prepared main view to two selectable main views:

- `Day Grid`
- `Social Graph`

Switching between them should update shared UI state and the URL without
destroying persistent global filter selections.

### Top-Bar Direction

When `view=day_grid`:

- row 1 shows main-view navigation and global filters
- row 2 shows `grid views`

When `view=social_graph`:

- row 1 still shows main-view navigation and global filters
- row 2 is hidden

### UI Transport Direction

Add UI transport code for the social-graph endpoint:

- request types
- response types
- query wiring
- projection adapters only if the raw transport shape is not directly usable

This transport must remain separate from timeline grid transport.

### Social-Graph View Scaffold Direction

Introduce the initial `SocialGraphView` container with:

- loading state
- error state
- empty state
- ready state shell

The ready state may initially render a static placeholder frame or debug
projection view. The force simulation itself belongs to the next task.

### State Direction

Timeline-only state such as day hover and right-side hover panels must not leak
into the social-graph runtime.

Global filter state remains shared.
Social-graph interaction state is introduced only where required for the shell.

## Out of Scope

- no final force-directed rendering yet
- no advanced graph interactions yet
- no attempt to reuse the timeline split layout for the social graph if it does
  not fit the mode

## Acceptance Criteria

- the UI exposes a working `Social Graph` main-view button
- switching main views preserves global filter state
- `grid views` are hidden when the social graph is active
- the social graph issues its own API request and handles loading, error, and
  empty states
- the social-graph shell is structurally separate from the day-grid layout

## Notes

This task should prove the main-view architecture before investing in the
physics renderer. If the shell still feels like a hacked extension of the day
grid at this stage, the architecture is not yet clean enough.
