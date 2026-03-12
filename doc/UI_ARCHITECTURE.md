# PixelPast – UI Architecture

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
- clear separation between projection data and domain data
- responsive hover interactions
- persistent filter state
- derived view switching
- incremental feature growth without full rewrites

The architecture should optimize for clarity, predictability, and composability.

---

## 3. Technology Direction

Recommended stack:

- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query for server data fetching
- Zustand or React Context for lightweight UI state
- D3 only where needed for grid math or scales
- Plain React rendering first; avoid premature visualization complexity

No heavy charting framework should control the main grid.

---

## 4. Core UI Layers

The UI should be organized into four conceptual layers:

### A. App Shell
Responsible for layout, routing, top bar, and persistent panels.

### B. View Layer
Responsible for rendering the grid and contextual panels.

### C. Projection Layer
Responsible for transforming API responses into UI-ready structures such as:
- year grid cells
- timeline entries
- person highlights
- tag highlight states
- map point projections

### D. State Layer
Responsible for UI state such as:
- hovered date
- selected filters
- active view mode
- selected date range
- panel state

Domain models from the backend must not be used directly as rendering contracts.
The UI should consume projection DTOs.

---

## 5. Primary UI Modules

Recommended component structure:

- `AppShell`
- `TopBar`
- `YearGridStack`
- `YearGrid`
- `DayCell`
- `RightPanel`
  - `PersonsPanel`
  - `TagsPanel`
  - `MapPanel`
- `TimelinePreview` (optional later)
- `ViewModeSelector`
- `FilterBar`

---

## 6. Data Contracts

The UI should consume explicit projection endpoints instead of raw database entities.

Initial API-facing projection types should include:

### HeatmapDayProjection
Represents one day cell in the calendar grid.

Example fields:
- `date`
- `year`
- `activity_score`
- `color_value`
- `has_data`
- `event_count`
- `asset_count`

### DayContextProjection
Represents contextual data for a hovered or selected day.

Example fields:
- `date`
- `persons`
- `tags`
- `map_points`
- `summary_counts`

### TimelineEntryProjection
Represents a chronological row in future day detail views.

Example fields:
- `kind` (`event` | `asset`)
- `type` (`photo` | `video` | `calendar` | `music_play` | ...)
- `timestamp`
- `title`
- `summary`
- `coordinates`

The UI must treat these as view contracts, not inferred structures.

---

## 7. State Model

There are two categories of state:

### A. Ephemeral Interaction State
Short-lived and not persisted in URL.

Examples:
- `hoveredDate`
- `hoveredYear`
- `hoveredPanelItem`

This state exists only for exploration and contextual highlighting.

### B. Persistent Exploration State
Stored in URL and/or global store.

Examples:
- `viewMode`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`
- `selectedDerivedView`

This state controls recoloring and filtering of the grid.

---

## 8. Interaction Model

The architecture must support two distinct interaction modes:

### Hover
Temporary contextual inspection.

Effects:
- highlight one day
- update persons panel
- update tags panel
- update map points

### Selection / Filter
Persistent exploration mode.

Effects:
- recolor matching days
- restrict or reinterpret context panels
- remain stable across navigation and refresh

Hover must never mutate persistent filter state.

---

## 9. URL Strategy

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
- predictable back/forward navigation

Ephemeral hover state must not be encoded in the URL.

---

## 10. Rendering Strategy

The main grid should initially be rendered using standard React components.

Start with:
- one component per year
- one component per day cell

Only optimize further if needed.

Do not start with Canvas or WebGL.
Do not introduce D3-driven DOM ownership for the whole UI.

Performance expectations for v1:
- 10–30 years
- approximately 365 cells per year
- dynamic recoloring
- lightweight hover interactions

This should be manageable with straightforward React rendering if the data model is clean and components are memoized where appropriate.

---

## 11. Layout Strategy

Desktop-first layout:

- Left side: fixed-primary grid region
- Right side: contextual side panels
- Top bar: global controls

The grid must always remain visible.
Context panels must never replace it.

Recommended top-level layout structure:

- `TopBar`
- `MainSplitLayout`
  - `LeftGridPane`
  - `RightContextPane`

---

## 12. Panel Responsibilities

### PersonsPanel
- display persons relevant to hovered day or active filters
- allow selecting one or more persons
- reflect active state visually

### TagsPanel
- display tags relevant to hovered day or active filters
- allow selecting tag paths or subtrees
- reflect active state visually

### MapPanel
- show points relevant to hovered day or active filters
- remain visually quiet by default
- act as contextual support, not dominant navigation

---

## 13. Derived Views

Derived views are backend-defined color strategies over time.

The UI should treat them as selectable view modes with stable identifiers.

Examples:
- `activity`
- `travel`
- `sports`
- `party_probability`

The frontend should not implement analytics logic.
It should request the appropriate projection and render it.
Available projections are also fetched from api once on startup.

---

## 14. Styling Principles

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

## 15. Evolution Strategy

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

## 16. Non-Negotiable Rules

- The grid is always visible.
- Time is the primary organizing principle.
- Projection DTOs are the UI contract.
- Hover state is ephemeral.
- Filter state is persistent.
- UI simplicity beats feature density.
- Avoid premature rendering complexity.
