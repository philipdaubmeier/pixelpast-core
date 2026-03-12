# R-008 – Hover Synchronization Across Grid and Context Panels

## Goal

Implement ephemeral hover-driven synchronization between the grid and the
right-side contextual panels.

This establishes the core exploration interaction model.

---

## Scope

Implement hover state for a day cell.

On hover of a grid cell:

- mark the hovered date in UI state
- update PersonsPanel with mocked day context data
- update TagsPanel with mocked day context data
- update MapPanel with mocked day context data
- visually highlight the hovered cell

Hover behavior must be:

- temporary
- non-persistent
- independent from filter state
- cleared when no cell is hovered

Create a mocked DayContextProjection contract to support this interaction.

---

## Out of Scope

- No real backend integration
- No persistent selection/filter state
- No URL synchronization
- No timeline day detail page
- No multi-hover or range-hover behavior

---

## Acceptance Criteria

- Hovering a cell updates all contextual panels
- Leaving the grid clears hover state
- Hover does not mutate persistent selection state
- UI behavior is stable and lightweight

---

## Notes

This is the first true interaction task.
Keep hover state simple and explicit.
Do not mix hover and filter logic.
