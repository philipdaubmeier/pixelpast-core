# PixelPast - UI Architecture

## 1. Purpose

The PixelPast UI is a desktop-first visual exploration interface centered on chronology.

Its primary responsibility is not editing or data management.
Its primary responsibility is to make time explorable.

The day grid is the core projection surface.
All other UI elements exist to contextualize, filter, and reinterpret that surface.

For additional projections the architecture must support:

- one shared shell
- multiple main exploration views
- persistent global filters across those views
- explicit data contracts per projection

---

## 2. Architectural Goals

The UI architecture must support:

- stable rendering of multi-year calendar grids
- a separate social-graph projection with its own rendering runtime
- explicit separation between backend domain data and frontend projection data
- server-side execution of persistent timeline filters
- persistent global filter state and reproducible URLs
- view-local interaction state that does not leak across main views
- incremental feature growth without forcing unrelated projections into one
  layout model

The architecture should optimize for clarity, predictability, and composability.

---

## 3. Technology Direction

Recommended stack:

- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query for server data fetching
- a small dedicated UI state layer such as React Context or Zustand
- D3 only where it materially helps, such as force simulation for the social
  graph or tightly scoped grid math

No heavy charting framework should own the application shell.
React should own view switching and application structure.

---

## 4. Workspace and Module Boundaries

The UI should live in a dedicated frontend workspace at the repository root:
`ui/`.

Within that workspace, organize code by responsibility:

- `app/` for shell, main-view navigation, layout, and bootstrapping
- `components/` for reusable presentational building blocks
- `features/timeline/` for the day-grid projection and timeline-specific
  interactions
- `features/context/` for timeline context panels such as persons, tags, and
  map
- `features/social-graph/` for graph-specific transport adapters, view logic,
  and rendering
- `api/` for HTTP clients and request wiring
- `projections/` for UI-facing DTOs and transformation helpers
- `state/` for shared UI state and URL synchronization
- `mocks/` for static fixtures used before real API integration

Avoid mixing transport DTOs, UI projection DTOs, and local component state into
one generic folder.

---

## 5. Core UI Layers

The UI should be organized into four conceptual layers:

### A. App Shell

Responsible for:

- top bar
- main-view navigation
- persistent global filters
- URL synchronization
- selecting which primary view is mounted

### B. View Layer

Responsible for rendering one mounted main view at a time, for example:

- `DayGridView`
- `SocialGraphView`

### C. Projection Layer

Responsible for transforming API responses into UI-ready structures such as:

- year grid cells
- day context payloads
- timeline entries
- person highlight state
- tag highlight state
- map point projections
- social-graph nodes
- social-graph links

### D. State Layer

Responsible for cross-component UI state such as:

- active main view
- active grid view
- selected global filters
- selected date range
- timeline hover state
- graph-local hover and focus state where needed

Backend domain models must not be used directly as rendering contracts.
The UI should consume explicit projection DTOs.

---

## 6. Primary UI Modules

Recommended main modules:

- `AppShell`
- `TopBar`
- `MainViewSelector`
- `GlobalFilterBar`
- `GridViewSelector`
- `DayGridView`
- `MainSplitLayout`
- `LeftGridPane`
- `RightContextPane`
- `YearGridStack`
- `YearGrid`
- `DayCell`
- `PersonsPanel`
- `TagsPanel`
- `MapPanel`
- `SocialGraphView`
- `SocialGraphCanvas` or `SocialGraphSurface`

`TimelinePreview` or richer day storytelling can be added later.

---

## 7. Data Contracts

The UI should consume explicit projection endpoints instead of raw database
entities.

### `ExplorationBootstrapProjection`

Represents lightweight shell/bootstrap metadata for the day-grid mode.

Suggested fields:

- `range`
- `grid_views`
- `persons`
- `tags`

### `ExplorationGridDayProjection`

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
Persistent timeline filtering should be applied server-side before this data
reaches the browser.

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

### `SocialGraphProjection`

Represents the social-graph main view.

Suggested fields:

- `persons`
- `links`

Suggested person fields:

- `id`
- `name`
- `occurrence_count`

Suggested link fields:

- `person_ids`
- `weight`

The frontend should treat these contracts as stable UI-facing shapes, not
inferred backend internals.

---

## 8. State Model

There are three categories of UI state:

### A. Global Persistent State

Stored in the URL and shared across main views where appropriate.

Examples:

- `mainView`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`

### B. View-Local Persistent State

Persistent, but meaningful only inside one main view.

Examples:

- `gridView` for `Day Grid`
- graph mode or layout preferences if later introduced for `Social Graph`

### C. Ephemeral Interaction State

Short-lived and not persisted in the URL.

Examples:

- `hoveredDate`
- `hoveredPanelItem`
- `hoveredSocialNode`
- current simulation tick state

---

## 9. Interaction Model

The architecture must support three distinct interaction scopes:

### Main-View Navigation

Changes which primary projection is mounted.

Effects:

- update the URL-backed `mainView`
- unmount the inactive view runtime
- preserve global filter state

### Hover

Temporary contextual inspection within the active main view.

Effects:

- update local contextual highlight
- never mutate persistent filter state

### Selection and Filter

Persistent analytical framing.

Effects:

- update the URL
- trigger the active view's data fetch and rendering path
- remain stable across refresh and navigation

Hover adds temporary focus.
Selection defines a durable interpretation of the active projection.

---

## 10. URL Strategy

Persistent exploration state should be representable in the URL.

Examples:

- `mainView=day_grid`
- `mainView=social_graph`
- `gridView=calendar`
- `persons=anna,tina`
- `tags=place/italy,travel/summer`
- `from=2018-01-01`
- `to=2025-12-31`

This allows:

- shareable views
- reproducibility
- refresh-safe exploration
- predictable back and forward navigation

Ephemeral hover state and simulation runtime state must not be encoded in the
URL.

---

## 11. Rendering Strategy

### Day Grid

The day grid should continue to render with standard React components.

Start with:

- one component per year
- one component per day cell

Do not hand DOM ownership of the entire timeline to D3.

### Social Graph

The social graph may use SVG or Canvas, with D3-force or equivalent simulation
logic for layout.

React should still own:

- mounting and unmounting the view
- view-local controls
- loading and error states

Heavy graph runtime work such as a live force simulation should be torn down
when the user leaves the main view. Cacheable query data may remain.

---

## 12. Layout Strategy

Desktop-first shell:

- top bar across the full width
- row 1 for main-view navigation and global filters
- row 2 for view-specific secondary controls when the active main view needs
  them

Recommended main-view layouts:

### `Day Grid`

- `TopBar`
- `MainSplitLayout`
  - `LeftGridPane`
  - `RightContextPane`

### `Social Graph`

- `TopBar`
- dedicated graph surface layout
- optional graph-local overlays or legends

The app shell should not force every main view into the day-grid split layout.

---

## 13. Panel Responsibilities

### `PersonsPanel`

- display persons relevant to the hovered day or active timeline filters
- allow selecting one or more persons
- reflect active state visually

### `TagsPanel`

- display tags relevant to the hovered day or active timeline filters
- allow selecting tag paths or subtrees
- reflect active state visually

### `MapPanel`

- show points relevant to the hovered day or active timeline filters
- remain visually quiet by default
- act as contextual support, not dominant navigation

Timeline context panels are timeline-specific. They should not be assumed to
exist in every main view.

---

## 14. Grid Views

Grid views are backend-defined coloring strategies over time.

Examples:

- `activity`
- `calendar`
- `music`
- `vacation`

They are secondary controls inside the `Day Grid` main view.
They are not app-level navigation modes.

The frontend should not implement analytics logic.
It should request the relevant grid projection and render it.

---

## 15. Styling Principles

- minimal shell chrome
- clear main-view hierarchy in the top bar
- global filters visually stronger than secondary subview toggles
- color is primary encoding in the grid
- no icons inside day cells
- strong whitespace discipline
- low visual noise
- typography should support scanning, not decoration

Light mode by default, optionally dark mode later on.

---

## 16. Evolution Strategy

The UI should evolve in this order:

1. app shell and day-grid layout
2. static year-grid rendering
3. hover synchronization
4. persistent filter state
5. grid-view switching
6. main-view navigation split
7. social-graph API and shell
8. social-graph rendering
9. richer projection-specific storytelling

This ordering preserves architectural stability while enabling incremental
delivery.

---

## 17. Non-Negotiable Rules

- one main view is active at a time
- the day grid remains the default chronology projection
- global filters remain app-level state
- grid views are secondary controls inside `Day Grid`
- projection DTOs are the UI contract
- hover state is ephemeral
- persistent filter evaluation belongs on the server where the projection
  requires it
- inactive heavy runtimes must be torn down
- UI simplicity beats feature density
