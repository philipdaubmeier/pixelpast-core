# PixelPast - UI Architecture

## 1. Purpose

The PixelPast UI is a desktop-first visual exploration interface centered on chronology.

Its primary responsibility is not editing or data management.
Its primary responsibility is to make time explorable.

The calendar grid is the core projection surface.
All other UI elements exist to contextualize, filter, and reinterpret that surface.

---

## 2. Architectural Goals

The UI architecture must support:

- stable rendering of multi-year calendar grids
- explicit separation between backend domain data and frontend projection data
- lightweight hover-driven context updates
- persistent filter state and reproducible views
- server-side execution of persistent timeline filters
- incremental feature growth without architectural rewrites

The architecture should optimize for clarity, predictability, and composability.

---

## 3. Technology Direction

Recommended stack:

- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query for server data fetching
- a small dedicated UI state layer such as Zustand or React Context
- D3 only for calendar math or color scales when React and plain TypeScript are not enough

No heavy charting framework should control the main grid.

---

## 4. Workspace and Module Boundaries

The UI should live in a dedicated frontend workspace at the repository root.
Recommended directory name: `ui/`.

Within that workspace, organize code by responsibility:

- `app/` for shell, layout, routing, and bootstrapping
- `components/` for reusable presentational building blocks
- `features/timeline/` for the grid and timeline-focused interaction logic
- `features/context/` for persons, tags, and map panels
- `api/` for HTTP clients and request wiring
- `projections/` for UI-facing DTOs and transformation helpers
- `state/` for shared UI state and URL synchronization
- `mocks/` for static fixtures used before real API integration

Avoid mixing transport DTOs, UI projection DTOs, and local component state into one generic folder.

---

## 5. Core UI Layers

The UI should be organized into four conceptual layers:

### A. App Shell

Responsible for layout, routing, top bar, and persistent panels.

### B. View Layer

Responsible for rendering the grid and contextual panels.

### C. Projection Layer

Responsible for transforming API responses into UI-ready structures such as:

- year grid cells
- day context payloads
- timeline entries
- person highlight state
- tag highlight state
- map point projections

### D. State Layer

Responsible for cross-component UI state such as:

- hovered date
- selected filters
- active view mode
- selected date range
- panel state

Backend domain models must not be used directly as rendering contracts.
The UI should consume explicit projection DTOs.

---

## 6. Primary UI Modules

Recommended first-pass component structure:

- `AppShell`
- `TopBar`
- `MainSplitLayout`
- `LeftGridPane`
- `RightContextPane`
- `YearGridStack`
- `YearGrid`
- `DayCell`
- `PersonsPanel`
- `TagsPanel`
- `MapPanel`
- `ViewModeSelector`
- `FilterBar`

`TimelinePreview` or richer day storytelling can be added later.

---

## 7. Data Contracts

The UI should consume explicit projection endpoints instead of raw database entities.

Initial projection contracts should include:

### `ExplorationBootstrapProjection`

Represents lightweight shell/bootstrap metadata.

Suggested fields:

- `range`
- `view_modes`
- `persons`
- `tags`

### `HeatmapDayProjection`

Represents one day cell in the calendar grid.

Suggested fields:

- `date`
- `year`
- `week_index`
- `weekday_index`
- `activity_score`
- `color_value`
- `has_data`

The grid projection should stay intentionally small.
Persistent filtering should be applied server-side before this data reaches the
browser.

### `DayContextProjection`

Represents contextual data for a hovered day.

Suggested fields:

- `date`
- `persons`
- `tags`
- `map_points`
- `summary_counts`

### `TimelineEntryProjection`

Represents a chronological row in a future day detail view.

Suggested fields:

- `kind` (`event` or `asset`)
- `type`
- `timestamp`
- `title`
- `summary`
- `coordinates`

The frontend should treat these contracts as stable UI-facing shapes, not inferred backend internals.

---

## 8. State Model

There are two categories of UI state:

### A. Ephemeral Interaction State

Short-lived and not persisted in the URL.

Examples:

- `hoveredDate`
- `hoveredPanelItem`

This state exists only for temporary exploration and contextual highlighting.

### B. Persistent Exploration State

Stored in the URL and mirrored in shared UI state.

Examples:

- `viewMode`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`

This state defines the current exploration frame and drives backend requests for
the filtered grid.

---

## 9. Interaction Model

The architecture must support two distinct interaction modes:

### Hover

Temporary contextual inspection.

Effects:

- highlight one day
- update persons, tags, and map panels
- never mutate persistent filter state

### Selection and Filter

Persistent exploration mode.

Effects:

- request and render a server-filtered grid
- update the URL
- remain stable across refresh and navigation

Hover adds temporary focus.
Selection defines the durable interpretation of the grid.

---

## 10. URL Strategy

Persistent exploration state should be representable in the URL.

Examples:

- `viewMode=travel`
- `persons=anna,tina`
- `tags=place/italy,travel/summer`
- `from=2018-01-01`
- `to=2025-12-31`

This allows:

- shareable views
- reproducibility
- refresh-safe exploration
- predictable back and forward navigation

Ephemeral hover state must not be encoded in the URL.

---

## 11. Rendering Strategy

The main grid should initially be rendered with standard React components.

Start with:

- one component per year
- one component per day cell

Do not start with Canvas or WebGL.
Do not hand DOM ownership of the whole grid to D3.

Target for the first implementation:

- 10 to 30 years
- roughly 365 cells per year
- dynamic recoloring
- lightweight hover interactions

Optimize only after profiling shows a real need.

---

## 12. Layout Strategy

Desktop-first layout:

- top bar across the full width
- left side for the primary grid region
- right side for contextual panels stacked vertically

The grid must always remain visible.
Context panels must never replace it.

Recommended top-level layout:

- `TopBar`
- `MainSplitLayout`
  - `LeftGridPane`
  - `RightContextPane`

---

## 13. Panel Responsibilities

### `PersonsPanel`

- display persons relevant to the hovered day or active filters
- allow selecting one or more persons
- reflect active state visually

### `TagsPanel`

- display tags relevant to the hovered day or active filters
- allow selecting tag paths or subtrees
- reflect active state visually

### `MapPanel`

- show points relevant to the hovered day or active filters
- remain visually quiet by default
- act as contextual support, not dominant navigation

---

## 14. Derived Views

Derived views are backend-defined color strategies over time.

Examples:

- `activity`
- `travel`
- `sports`
- `party_probability`

The frontend should not implement analytics logic.
It should request the relevant projection and render it.

The list of available view modes may be fetched from the API later, but the first UI increment can use a small mocked list.

---

## 15. Styling Principles

- Minimalist
- Grid-first
- Color is primary encoding
- No icons inside day cells
- Strong whitespace discipline
- Low visual noise
- Typography should support scanning, not decoration
- Modern, clean geometric fonts, semi-light or even thin font weights for larger text sizes

Light mode by default, optionally dark mode later on.

---

## 16. Evolution Strategy

The UI should evolve in this order:

1. app shell and layout
2. static year grid rendering
3. hover synchronization
4. persistent filter state
5. derived view switching
6. richer contextual panels
7. day detail storytelling

This ordering preserves architectural stability while enabling incremental delivery.

---

## 17. Non-Negotiable Rules

- The grid is always visible.
- Time is the primary organizing principle.
- Projection DTOs are the UI contract.
- Hover state is ephemeral.
- Filter state is persistent.
- Persistent filter evaluation belongs on the server.
- UI simplicity beats feature density.
- Avoid premature rendering complexity.
