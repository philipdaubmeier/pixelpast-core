# PixelPast - UI States

## 1. Purpose

This document defines the UI state model for PixelPast.

Its goal is to make interaction behavior explicit before implementation.
It separates:

- global persistent state shared across main views
- persistent state that belongs to one main view only
- ephemeral interaction state

The state model must preserve these rules:

- chronology remains the product backbone
- the day grid is the default main view
- global filters survive main-view switches
- hover provides temporary context
- heavy inactive runtimes should be torn down without losing durable state

---

## 2. State Categories

PixelPast uses three primary categories of UI state.

### A. Global Persistent State

Long-lived state shared across main views.

Characteristics:

- stored in the URL where reasonable
- survives refresh and main-view switching
- belongs to the app shell rather than one feature module

Examples:

- active main view
- selected persons
- selected tags
- selected date range
- selected geographic filter

### B. View-Local Persistent State

Long-lived state that belongs to one main view.

Characteristics:

- may be stored in the URL
- survives leaving and re-entering the same main view
- should not be interpreted by unrelated main views

Examples:

- active `gridView` inside `Day Grid`
- future social-graph layout preferences

### C. Ephemeral Interaction State

Short-lived state used for immediate interaction feedback.

Characteristics:

- not stored in the URL
- cleared automatically when interaction ends or the view unmounts
- must not silently change persistent filter logic

Examples:

- currently hovered date
- currently hovered person chip
- currently hovered graph node
- currently hovered graph link

---

## 3. Core State Model

### 3.1 Global Persistent State

#### `mainView: MainView`

The active product-level projection.

Initial values:

- `day_grid`
- `social_graph`

Responsibilities:

- determine which main view is mounted
- shape top-bar secondary controls
- influence which query path is active

Rules:

- must always have a value
- should be represented in the URL
- defaults to `day_grid`

#### `selectedPersons: string[]`

The currently selected person identifiers.

Responsibilities:

- persist a person-based global exploration filter or focus
- remain stable across main-view switches
- visually mark active person selections in shared controls

Rules:

- multi-select is allowed
- order is not semantically meaningful
- should be represented in the URL
- an empty array means no person selection

#### `selectedTags: string[]`

The currently selected tag paths.

Responsibilities:

- persist a tag-based global exploration filter
- remain stable across main-view switches
- visually mark active tag selections in shared controls

Rules:

- values are hierarchical paths
- multi-select is allowed
- should be represented in the URL
- an empty array means no tag selection

Examples:

- `place/italy`
- `travel/summer`
- `people/family`

#### `selectedGeoFilter: GeoFilter | null`

Optional geographic filter applied where a main view can interpret it cleanly.

This remains future-facing, but the state model should leave space for it.

#### `selectedDateRange: DateRange | null`

Optional date range restriction for exploration.

Responsibilities:

- restrict or focus the active projection
- remain durable across main-view switches

Rules:

- should be represented in the URL when active
- should remain independent from hover state

### 3.2 View-Local Persistent State

#### `gridView: string`

The active day-grid coloring mode.

Examples:

- `activity`
- `calendar`
- `vacation`

Responsibilities:

- determine the day-grid color strategy
- influence day-grid data requests
- remain stable when leaving and returning to `Day Grid`

Rules:

- must always have a value
- should be represented in the URL
- is meaningful only when `mainView=day_grid`

### 3.3 Ephemeral State

#### `hoveredDate: string | null`

The currently hovered day in ISO date format (`YYYY-MM-DD`).

Responsibilities:

- highlight the hovered day cell
- drive contextual updates in persons, tags, and map panels
- show temporary day-level context

Rules:

- belongs only to `Day Grid`
- must be `null` when no day cell is hovered
- must not be encoded in the URL

#### `hoveredPanelItem: HoveredPanelItem | null`

Represents an optional hovered timeline-context item.

Possible kinds:

- `person`
- `tag`
- `map_point`

Purpose:

- temporary cross-panel highlighting
- optional visual feedback for timeline interactions

#### `hoveredSocialNodeId: string | null`

Optional hovered person id inside the social graph.

Rules:

- belongs only to `Social Graph`
- must be cleared when the view unmounts

#### `hoveredSocialLink: [string, string] | null`

Optional hovered social-graph link represented by its person-id pair.

Rules:

- belongs only to `Social Graph`
- must be cleared when the view unmounts

---

## 4. Derived State

Some UI values should not be persisted directly.
They should be derived from primary state and projection data.

Examples:

### `activeDayContext`

Derived from:

- `hoveredDate`
- loaded `DayContextProjection`

### `gridQueryKey`

Derived from:

- `mainView`
- `gridView`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`

This identifies the server request for the current day-grid frame.

### `socialGraphQueryKey`

Derived from:

- `mainView`
- supported global filter dimensions for the social graph
- optional graph-specific query inputs if later introduced

This identifies the server request for the current social-graph frame.

### `isGridViewSelectorVisible`

Derived from:

- `mainView`

Rules:

- `true` only when `mainView=day_grid`

Derived state must never become a second source of truth.

---

## 5. State Ownership

State should be owned at the lowest level that still preserves coherence.

Recommended shared state ownership in the app shell:

- `mainView`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`
- `gridView`

Recommended feature-level ephemeral state:

- `hoveredDate`
- `hoveredPanelItem`
- `hoveredSocialNodeId`
- `hoveredSocialLink`
- graph simulation internals

Recommended local component state:

- expanded or collapsed sections
- local input text
- transient UI affordances that do not affect other modules

Do not duplicate persistent state across multiple components.

---

## 6. URL-Backed State

The following state should be URL-addressable:

- `mainView`
- `gridView`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`

Suggested query parameter examples:

- `mainView=day_grid`
- `mainView=social_graph`
- `gridView=calendar`
- `persons=john,jimmy`
- `tags=place/italy,travel/summer`
- `from=2018-01-01`
- `to=2025-12-31`

Geographic filters may later use a compact serialized representation.

The following state must not be URL-backed:

- `hoveredDate`
- `hoveredPanelItem`
- `hoveredSocialNodeId`
- `hoveredSocialLink`
- graph simulation velocity, coordinates, or tick state

---

## 7. Interaction Rules

### 7.1 Main-View Switch Rules

Main-view switching is persistent and structural.

When a user switches main view:

- update `mainView`
- update the URL
- preserve global persistent filters
- preserve view-local persistent state for the view being left
- clear or unmount ephemeral state owned by the inactive view

One important runtime rule:

- leaving `Social Graph` should stop the force simulation and tear down
  graph-local listeners

### 7.2 Hover Rules

Hover is ephemeral and contextual.

When a user hovers a day cell:

- set `hoveredDate`
- visually highlight the cell
- update persons, tags, and map panels with day context
- do not change persistent filters
- do not change URL state

When a user hovers a graph node or link:

- update the relevant graph-local hover state
- do not mutate timeline hover state
- do not change URL state

When hover ends:

- clear the corresponding hover state

### 7.3 Selection Rules

Selection is persistent and analytical.

When a user selects a person, tag, main view, or grid view:

- update persistent state
- update the URL
- trigger the active view's relevant data path
- visually mark active selections

Selections remain active until explicitly changed or cleared.

### 7.4 Hover vs. Selection Precedence

Hover never overrides persistent selection.
It only adds temporary focus.

Examples:

- if person filters are active and a day is hovered, the hovered day context is
  shown inside the already selected exploration frame
- if a person is selected globally and a graph node is hovered, the hover adds
  temporary emphasis without clearing the durable selection

Persistent state defines the exploration frame.
Hover defines the temporary inspection target.

---

## 8. Data Fetching Implications

The state model implies three broad categories of data fetching.

### A. Day-Grid Projection Fetching

Depends on persistent state such as:

- `mainView`
- `gridView`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`

This data should be requested only when `mainView=day_grid`.

### B. Day-Context Fetching

Depends primarily on:

- `hoveredDate`
- the currently visible preloaded day-context range

This data is timeline-specific and should not be fetched while another main
view is active.

### C. Social-Graph Fetching

Depends on:

- `mainView`
- supported global filter dimensions for the social graph

This data should be requested only when `mainView=social_graph`.

The active main view determines which projection fetch path is live.

---

## 9. Suggested Type Model

Example TypeScript model:

```ts
type MainView = "day_grid" | "social_graph";

type DateRange = {
  from: string;
  to: string;
};

type GeoFilter =
  | {
      kind: "radius";
      latitude: number;
      longitude: number;
      radiusMeters: number;
    }
  | {
      kind: "bbox";
      minLatitude: number;
      maxLatitude: number;
      minLongitude: number;
      maxLongitude: number;
    };

type HoveredPanelItem =
  | { kind: "person"; id: string }
  | { kind: "tag"; path: string }
  | { kind: "map_point"; id: string };

type PixelPastUiState = {
  mainView: MainView;
  gridView: string;
  selectedPersons: string[];
  selectedTags: string[];
  selectedGeoFilter: GeoFilter | null;
  selectedDateRange: DateRange | null;
  hoveredDate: string | null;
  hoveredPanelItem: HoveredPanelItem | null;
  hoveredSocialNodeId: string | null;
  hoveredSocialLink: [string, string] | null;
};
```

---

## 10. First Increment Scope

For the first main-view-navigation increment, the minimum required shared state
is:

- `mainView`
- `gridView`
- `selectedPersons`
- `selectedTags`

For the first social-graph increment, the minimum additional ephemeral state is:

- `hoveredSocialNodeId`
- `hoveredSocialLink`

Optional and intentionally deferred:

- `selectedGeoFilter`
- `selectedDateRange`
- persisted graph-local preferences

This keeps the first multi-view slice small while preserving future
extensibility.

---

## 11. Non-Negotiable State Principles

- global filter state is persistent
- view-local state must not leak across unrelated main views
- hover state is ephemeral
- persistent state should be URL-representable
- inactive heavy runtimes must be torn down without losing durable state
- there must be no duplicated source of truth
- derived state must remain derived
