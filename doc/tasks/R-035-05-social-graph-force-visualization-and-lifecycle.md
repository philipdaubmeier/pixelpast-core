# R-035-05 - Social Graph Force Visualization and Lifecycle

## Goal

Implement the actual social-graph visualization as a force-directed network and
define its runtime lifecycle so it remains performant and well-bounded inside
the app shell.

## Dependencies

- `R-035-04`

## Scope

### Rendering Direction

Render persons as nodes and co-occurrence pairs as links.

Suggested visual semantics:

- node radius scales logarithmically from `occurrence_count`
- link stroke and force strength scale from `weight`
- all nodes repel each other
- collision handling prevents obvious overlap
- damping and velocity decay allow the layout to settle

Use React for the shell and D3-force or equivalent simulation logic for the
layout runtime.

### Interaction Direction

Add the minimum graph interactions needed for exploration:

- hover node
- hover link
- zoom and pan
- selected-person or focused-node affordance if needed for readability

Do not let graph-local interaction semantics mutate unrelated day-grid state.

### Lifecycle Direction

When the user leaves `Social Graph`:

- stop the force simulation
- remove graph-specific animation work
- tear down graph-local event listeners
- unmount the heavy renderer

Persistent global filters and cacheable graph data may remain in shared state or
query cache. The expensive visual runtime should not remain active off-screen.

### Performance Direction

Choose SVG or Canvas pragmatically based on the expected graph size.

The first implementation does not need to optimize for arbitrary graph scale,
but it should avoid obvious architectural traps such as keeping a live
simulation running when the view is inactive.

## Out of Scope

- no automatic community detection algorithm yet
- no persisted saved layouts
- no graph-editing affordances
- no inferred relationship labels

## Acceptance Criteria

- the social graph renders weighted links and sized person nodes
- heavier links produce visibly stronger attraction
- nodes no longer collapse into unreadable overlap under normal datasets
- zoom and pan work in the rendered graph
- leaving the main view tears down the simulation and graph-local runtime work

## Notes

This task should prioritize a bounded, readable first graph over premature
feature density. The important result is a stable and inspectable social
topology view, not a graph-analysis workstation.
