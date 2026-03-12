# R-009 – Persistent Filter State and Grid Recoloring

## Goal

Implement persistent exploration filters and use them to recolor the grid.

This establishes the second core interaction layer after hover.

---

## Scope

Implement persistent state for:

- selected persons
- selected tags
- selected view mode

Requirements:

- state survives panel interaction
- state drives grid recoloring
- active selections are visible in the UI
- selections can be added and removed
- filter state is represented in the URL

Implement mocked matching behavior using static projection data.

Examples:

- selecting a person highlights matching days
- selecting a tag highlights matching days
- selecting a derived view changes the coloring strategy

---

## Out of Scope

- No real backend filtering yet
- No geo filter yet
- No advanced boolean query builder
- No server-driven URL parsing beyond minimal implementation
- No day detail view

---

## Acceptance Criteria

- Selecting a person persists and recolors the grid
- Selecting a tag persists and recolors the grid
- Changing view mode recolors the grid
- URL reflects persistent state
- Refresh preserves state when possible
- Hover remains independent from selection

---

## Notes

This task establishes the durable exploration model.
Keep the state model explicit and simple.
Do not overload the UI with advanced filtering controls yet.
