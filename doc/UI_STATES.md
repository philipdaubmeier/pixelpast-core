# PixelPast – UI States

## 1. Purpose

This document defines the UI state model for PixelPast.

Its goal is to make interaction behavior explicit before implementation.
It separates ephemeral exploration state from persistent exploration state
and provides a stable mental model for future tasks.

The UI state model must preserve the core design principle of PixelPast:

- the calendar grid is the primary exploration surface
- hover provides temporary context
- selection provides persistent filtering
- time remains the central organizing dimension

---

## 2. State Categories

PixelPast uses two primary categories of UI state:

### A. Ephemeral Interaction State

Short-lived state used for temporary contextual exploration.

Characteristics:

- not stored in the URL
- cleared automatically when interaction ends
- must not change persistent filter logic
- must be lightweight and predictable

Examples:

- currently hovered date
- currently hovered person chip
- currently hovered tag chip
- currently hovered map point

---

### B. Persistent Exploration State

Longer-lived state used to shape the meaning and coloring of the grid.

Characteristics:

- stored in URL where reasonable
- survives refresh/navigation
- drives recoloring and filtering
- must be explicit and composable

Examples:

- selected persons
- selected tags
- selected view mode
- selected date range
- selected geographic filter

---

## 3. Core State Model

## 3.1 Ephemeral State

### `hoveredDate: string | null`

The currently hovered day in ISO date format (`YYYY-MM-DD`).

Responsibilities:
- highlight the hovered day cell
- drive contextual updates in persons/tags/map panels
- show temporary day-level context

Rules:
- must be `null` when no day cell is hovered
- must not be encoded in the URL
- must not affect persistent recoloring logic

---

### `hoveredPanelItem: HoveredPanelItem | null`

Represents an optional hovered contextual item.

Possible kinds:
- `person`
- `tag`
- `map_point`

Purpose:
- temporary cross-panel highlighting
- optional visual feedback for future interactions

This is not required for v1 but should be anticipated in the state model.

Example shape:

```ts
type HoveredPanelItem =
  | { kind: "person"; id: string }
  | { kind: "tag"; path: string }
  | { kind: "map_point"; id: string }
```

---

## 3.2 Persistent State

### `viewMode: string`

The currently active grid coloring mode.

Examples:
- `activity`
- `travel`
- `sports`
- `party_probability`

Responsibilities:
- determine grid color strategy
- influence contextual panel interpretation
- define which projection endpoint or data contract is active

Rules:
- must always have a value
- should be represented in the URL
- default is `activity`

---

### `selectedPersons: string[]`

The currently selected person identifiers.

Responsibilities:
- persist a people-based filter
- recolor matching days
- visually mark active person selections

Rules:
- multi-select allowed
- order should not matter semantically
- should be represented in the URL
- empty array means no person filter

---

### `selectedTags: string[]`

The currently selected tag paths.

Responsibilities:
- persist tag-based filtering
- recolor matching days
- visually mark active tag selections

Rules:
- tag values are hierarchical paths
- multi-select allowed
- should be represented in the URL
- empty array means no tag filter

Examples:
- `place/italy`
- `travel/summer`
- `people/family`

---

### `selectedGeoFilter: GeoFilter | null`

Optional geographic filter applied to assets/events with coordinates.

This is not required for the first UI slice but should be modeled now.

Possible filter forms:
- radius from point
- bounding box

Example shape:

```ts
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
```

Responsibilities:
- restrict or recolor matching days
- influence map rendering
- remain persistent until cleared

Rules:
- should be represented in the URL when active
- must not be mutated by hover behavior

---

### `selectedDateRange: DateRange | null`

Optional date range restriction for exploration.

Example shape:

```ts
type DateRange = {
  from: string; // YYYY-MM-DD
  to: string;   // YYYY-MM-DD
};
```

Responsibilities:
- restrict visible or highlighted days
- allow focused exploration across long histories

Rules:
- should be represented in the URL when active
- should be independent from hoveredDate

---

## 4. Derived State

Some UI values should not be persisted directly.
They should be derived from primary state and projection data.

Examples:

### `activeDayContext`
Derived from:
- `hoveredDate`
- loaded `DayContextProjection`

### `filteredHeatmapDays`
Derived from:
- `viewMode`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`
- loaded `HeatmapDayProjection[]`

### `activeFilterSummary`
Derived from:
- persistent exploration state

Examples:
- "2 persons selected"
- "Tag filter: place/italy"
- "View: travel"

Derived state should never become a second source of truth.

---

## 5. State Ownership

State should be owned at the lowest level that still preserves coherence.

Recommended ownership:

### App-level or global store
- `viewMode`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`
- `hoveredDate`

These values affect multiple panels and the grid simultaneously.

### Local component state
- temporary panel UI affordances
- expanded/collapsed sections
- local input text
- transient visual toggles that do not affect other modules

Do not duplicate persistent state in multiple components.

---

## 6. URL-Backed State

The following state should be URL-addressable:

- `viewMode`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`

Suggested query parameter examples:

- `viewMode=travel`
- `persons=john,jimmy`
- `tags=place/italy,travel/summer`
- `from=2018-01-01`
- `to=2025-12-31`

Geographic filters may later use a compact serialized representation.

The following state must not be URL-backed:

- `hoveredDate`
- `hoveredPanelItem`

---

## 7. Interaction Rules

## 7.1 Hover Rules

Hover is ephemeral and contextual.

When a user hovers a day cell:

- set `hoveredDate`
- visually highlight the cell
- update persons/tags/map panels with day context
- do not change persistent filters
- do not change URL state

When hover ends:

- clear `hoveredDate`
- clear any hover-based contextual highlights

---

## 7.2 Selection Rules

Selection is persistent and analytical.

When a user selects a person, tag, or view mode:

- update persistent state
- update URL
- recompute grid coloring
- visually mark active selections
- preserve state across refresh where possible

Selections remain active until explicitly changed or cleared.

---

## 7.3 Hover vs. Selection Precedence

Hover never overrides persistent selection.
It only adds temporary contextual focus.

Examples:

- if a person filter is active and a day is hovered, the hovered day context is shown within the already filtered interpretation
- if a tag filter is active, hover should not remove or replace that filter

Persistent state defines the exploration frame.
Hover defines the temporary inspection target.

As for the design, persistent states can for example be displayed by coloring the pixel squares, while hover states would add an outline or an outer glow effect to the squares.

---

## 8. Data Fetching Implications

The state model implies two broad categories of data fetching:

### A. Heatmap Projection Fetching
Depends on persistent state such as:
- `viewMode`
- `selectedPersons`
- `selectedTags`
- `selectedGeoFilter`
- `selectedDateRange`

This data is suitable for caching and refetching based on query keys.

### B. Day Context Fetching
Depends primarily on:
- `hoveredDate`
- active persistent filter context if needed

This data may be:
- lazily fetched on hover
- prefetched
- derived from already available local data in early versions

The UI architecture should keep these concerns separate.

Depending on first learnings of using the UI live, it may be decided to never fetch any data on hover but to preload all data needed for hover highlighting whilst or directly after fetching persistent states.

---

## 9. Suggested Type Model

Example TypeScript model:

```ts
type ViewMode =
  | "activity"
  | "travel"
  | "sports"
  | "party_probability";

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
  hoveredDate: string | null;
  hoveredPanelItem: HoveredPanelItem | null;

  viewMode: ViewMode;
  selectedPersons: string[];
  selectedTags: string[];
  selectedGeoFilter: GeoFilter | null;
  selectedDateRange: DateRange | null;
};
```

---

## 10. v1 Scope Guidance

For the first UI implementation, the minimum required state is:

- `hoveredDate`
- `viewMode`
- `selectedPersons`
- `selectedTags`

Optional but not required in the first iteration:

- `selectedGeoFilter`
- `selectedDateRange`
- `hoveredPanelItem`

This keeps the first UI slice small while preserving future extensibility.

---

## 11. Non-Negotiable State Principles

- Hover state is ephemeral.
- Filter state is persistent.
- Persistent state should be URL-representable.
- The grid reacts to persistent state.
- Context panels react to both hover and persistent state.
- No duplicated source of truth.
- Derived state must remain derived.
