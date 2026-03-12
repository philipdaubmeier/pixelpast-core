# R-012 - Persistent Filter State and Grid Recoloring

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

- no real backend filtering yet
- no geo filter yet
- no advanced boolean query builder
- no server-driven filter parsing beyond minimal URL sync
- no day detail view

---

## Acceptance Criteria

- selecting a person persists and recolors the grid
- selecting a tag persists and recolors the grid
- changing view mode recolors the grid
- the URL reflects persistent state
- refreshing the page restores state from the URL when possible
- hover remains independent from persistent selection
- filter matching logic is implemented in a dedicated state or projection layer, not scattered across panel components

---

## Notes

This task establishes the durable exploration model.
Keep the state model explicit and small.
Do not overload the UI with advanced filtering controls yet.
