# R-011 - Hover Synchronization Across Grid and Context Panels

## Goal

Implement ephemeral hover-driven synchronization between the grid and the right-side context panels.

This establishes the first core exploration interaction.

---

## Scope

Implement hover state for a day cell.

On hover of a grid cell:

- mark the hovered date in shared UI state
- update `PersonsPanel` with mocked day context data
- update `TagsPanel` with mocked day context data
- update `MapPanel` with mocked day context data
- visually highlight the hovered cell

Hover behavior must be:

- temporary
- non-persistent
- independent from filter state
- cleared when no cell is hovered

Create a mocked `DayContextProjection` contract to support this interaction.

---

## Out of Scope

- no real backend integration
- no persistent selection or filter state
- no URL synchronization
- no day detail page
- no range hover behavior

---

## Acceptance Criteria

- hovering a cell updates all three contextual panels
- leaving the cell or grid clears hover state
- hover does not mutate persistent selection state
- hover visuals are distinct from base cell coloring
- the implementation keeps day-context mock data separate from component markup

---

## Notes

This task introduces the first shared interaction state.
Keep hover behavior simple and explicit.
Do not mix hover logic with future selection logic.
