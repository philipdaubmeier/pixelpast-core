# R-007 – Year Grid Rendering (Static Projection)

## Goal

Render the primary multi-year GitHub-style calendar grid using static or mocked
projection data.

This task establishes the main product surface.

---

## Scope

Implement:

- YearGridStack
- YearGrid
- DayCell

Render:

- multiple years stacked vertically
- oldest year at top
- latest year at bottom
- rotated year label on the left
- one cell per day
- GitHub-style weekly column layout

Use mocked or local static data shaped like HeatmapDayProjection.

Each day cell must support:

- date
- activity/color value
- basic hover affordance
- empty state vs active state styling

Default scroll behavior:
- current year visible on initial load

---

## Out of Scope

- No backend integration
- No actual hover synchronization
- No persistent filter state
- No contextual panel updates
- No derived view switching

---

## Acceptance Criteria

- Grid renders multiple full years correctly
- Calendar alignment is stable and visually readable
- Empty and active cells are distinguishable
- Year ordering is correct
- Current year is visible by default

---

## Notes

This task is about rendering structure, not full behavior.
Keep cell visuals minimal.
Do not add icons or inline labels inside cells.
