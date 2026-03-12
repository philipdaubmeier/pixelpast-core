# R-006 – React UI Skeleton

## Goal

Create the initial PixelPast frontend application shell and layout foundation.

This task establishes the desktop-first UI structure without implementing
real data-driven visualizations yet.

---

## Scope

Create a frontend application using:

- React
- TypeScript
- Vite
- Tailwind CSS

Implement the following structural components:

- AppShell
- TopBar
- MainSplitLayout
- LeftGridPane
- RightContextPane
- PersonsPanel
- TagsPanel
- MapPanel

Create placeholder content for each section.

Layout requirements:

- top bar across full width
- left panel for the grid
- right panel for contextual views
- right panel split vertically into:
  - persons
  - tags
  - map

---

## Out of Scope

- No real API integration
- No real grid data
- No filter logic
- No hover logic
- No routing complexity beyond minimal app setup

---

## Acceptance Criteria

- Frontend app starts locally
- Layout matches UI_CONCEPT.md and UI_ARCHITECTURE.md
- Grid area and right panel are visibly separated
- Panels are reusable components, not inline markup
- No mock business logic inside components

---

## Notes

Keep the app shell clean and minimal.
Favor composable layout over visual polish.
Do not introduce heavy state management yet unless required.
