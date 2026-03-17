# R-035 - Primary View Navigation and Social Graph

## Goal

Introduce a first-class main-view navigation layer above the existing day-grid
experience and use it to add a new `Social Graph` exploration mode alongside
the existing `Day Grid`.

This feature is not a small panel addition. It is a product-level expansion
from one primary projection surface to multiple primary projections over the
same personal-history corpus.

The work should preserve the current strengths of the day grid while making the
new social graph feel like a peer exploration mode rather than an embedded
widget.

## Dependencies

- `R-017`
- `R-024-02`
- `R-031-04`
- `R-032`
- `R-034-05`

## Scope

This task series covers four architectural layers:

- app-shell navigation and state split between main views and grid-specific
  subviews
- a canonical read path and REST endpoint for person co-occurrence graph data
- UI transport and shell integration for switching into the new main view
- the actual force-directed social graph visualization

### Design Direction

The key conceptual change is:

- `Day Grid` becomes one main view
- current timeline `view modes` become `grid views`
- persistent filters remain globally owned and visible in the top bar
- the social graph is loaded through its own API contract and view runtime

The social graph is explicitly allowed to read from canonical data instead of a
derived day-level model because it is not a day-aggregate projection. Its
source of truth is person co-occurrence across assets.

## Subtasks

- `R-035-01` - Main-view navigation foundation and grid-view demotion
- `R-035-02` - Social graph canonical read model and projection contract
- `R-035-03` - Social graph API endpoint and backend exposure
- `R-035-04` - Social graph UI shell and transport integration
- `R-035-05` - Social graph force visualization and lifecycle hardening

## Out of Scope

- no `event_person` support in the first social graph increment
- no persisted graph layout coordinates or cluster snapshots
- no derived social-cluster tables
- no user-authored graph analytics formulas
- no automatic community labeling or relationship inference beyond weighted
  asset co-occurrence
- no attempt to keep the social-graph DOM or simulation alive while the user is
  on another main view

## Acceptance Criteria

- the app shell exposes `Day Grid` and `Social Graph` as distinct main views
- persistent filters remain visible and stable across main-view switches
- current timeline view modes are repositioned as day-grid-specific `grid views`
- a dedicated API endpoint returns social-graph projection data from canonical
  person and asset relationships
- the UI can switch into a social-graph mode, load that data, and render an
  interactive force-directed person network
- leaving the social graph tears down heavy view runtime work such as the force
  simulation while preserving durable exploration state

## Notes

This series deliberately treats the social graph as a separate projection, not
as a secondary panel. That keeps the app architecture clear:

- shared shell and filter state at the top
- separate primary projections underneath
- explicit data contracts per projection
