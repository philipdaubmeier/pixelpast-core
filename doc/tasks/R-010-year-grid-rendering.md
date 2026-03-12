# R-010 - Year Grid Rendering

## Goal

Render the primary multi-year GitHub-style calendar grid using static or mocked projection data.

This task establishes the main product surface.

---

## Scope

Implement:

- `YearGridStack`
- `YearGrid`
- `DayCell`

Render:

- multiple years stacked vertically
- oldest year at the top
- latest year at the bottom
- a year label on the left
- one cell per day
- weekly column layout

Use mocked or local static data shaped like `HeatmapDayProjection`.

Each day cell must support:

- `date`
- a color value or activity intensity
- clear empty-state versus active-state styling
- a basic hover affordance without cross-panel synchronization yet

Initial viewport behavior:

- current year visible on initial load

---

## Out of Scope

- no backend integration
- no contextual panel updates
- no persistent filter state
- no URL synchronization
- no derived view switching

---

## Acceptance Criteria

- grid renders multiple full years correctly
- calendar alignment is stable and visually readable
- empty and active cells are clearly distinguishable
- year ordering is correct
- current year is visible on first load
- the implementation uses reusable projection-shaped fixtures rather than ad hoc inline arrays

---

## Notes

This task is about rendering structure, not full behavior.
Keep cell visuals minimal.
Do not add icons or labels inside day cells.
