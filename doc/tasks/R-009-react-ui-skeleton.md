# R-009 - React UI Skeleton

## Goal

Create the initial PixelPast frontend workspace, application shell, and layout foundation.

This task establishes the desktop-first UI structure without implementing real data-driven visualizations yet.

---

## Scope

Create a dedicated frontend workspace using:

- React
- TypeScript
- Vite
- Tailwind CSS

Recommended workspace location:

- `ui/`

Implement the following structural components:

- `AppShell`
- `TopBar`
- `MainSplitLayout`
- `LeftGridPane`
- `RightContextPane`
- `PersonsPanel`
- `TagsPanel`
- `MapPanel`

Create placeholder content for each section.

Layout requirements:

- top bar across full width
- left pane reserved for the timeline grid
- right pane reserved for contextual views
- right pane stacked vertically into persons, tags, and map

Also establish:

- a minimal app entry point
- a global stylesheet and Tailwind wiring
- a small component folder structure aligned with `UI_ARCHITECTURE.md`

---

## Out of Scope

- no real API integration
- no real grid data
- no filter logic
- no hover logic
- no routing complexity beyond minimal bootstrapping

---

## Acceptance Criteria

- frontend app starts locally
- layout matches `UI_CONCEPT.md` and `UI_ARCHITECTURE.md`
- grid area and right-side context pane are visibly separated
- panels are reusable components, not inline markup in one file
- no mock business logic is embedded in presentational components
- the workspace structure leaves a clear place for future `api/`, `state/`, `projections/`, and `mocks/` modules

---

## Notes

Keep the shell clean and minimal.
Favor composable layout over visual polish.
Do not introduce heavy shared state management in this task unless it is required for application bootstrapping.
