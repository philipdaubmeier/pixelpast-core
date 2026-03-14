# PixelPast - UI Concept

## 1. Intuition

PixelPast is not a dashboard.
It is not a CRUD interface.
It is a visual exploration instrument.

The UI exists to make time explorable.

The calendar grid is not a component.  
It is the product.

Everything else in the interface exists to contextualize, filter, enrich, or reinterpret the grid.

If a UI decision weakens the clarity of chronological exploration, it is the wrong decision.

---

## 2. Core Design Principles

1. Calendar-first.
2. All years visible at once.
3. Grid is always visible.
4. Exploration over editing.
5. Hover for context.
6. Selection for filtering.
7. Visual simplicity over density.
8. Desktop-first.

---

## 3. High-Level Layout

The UI is divided into two primary panels.

```text
┌────────────────────────────────────────────────────────────┐
│ TOP BAR                                                    │
│ [ View Mode ] [ Filters ] [ Search ] [ Derived Views ]     │
├────────────────────────────────────────────────────────────┤
│ LEFT PANEL                      RIGHT PANEL                |
│ ┌───────────────────────────┐   ┌──────────────────────┐   │
│ │                           │   │ Persons              │   │
│ │                           │   ├──────────────────────┤   |
│ │     YEAR GRID STACK       │   │ Tags                 │   |
│ │                           │   ├──────────────────────┤   │
│ │                           │   │ Map                  │   │
│ │                           │   └──────────────────────┘   │
│ │                           │                              │
│ └───────────────────────────┘                              │
└────────────────────────────────────────────────────────────┘
```

### Left Panel – Timeline Grid

- GitHub-style calendar grid.
- All years stacked vertically.
- Oldest year at top.
- Most recent year at bottom.
- Scroll vertically to move through time.
- Year labels rotated 90° counter clock wise on the left.
- Default scroll position: current year visible.

The grid never disappears.

---

### Right Panel – Context Views

The right panel is horizontally divided into contextual views:

- Persons
- Tags
- Map
- (Future: additional analytics views)

These panels never replace the grid.
They react to it.

---

## 4. Chronological Structure

Time flows vertically.

Scrolling up = going into the past.  
Scrolling down = moving toward the present.

The grid is a continuous temporal surface.

Zooming (month/day) is out of scope for v1.

---

## 5. Interaction Model

There are two interaction layers:

### A. Soft Highlight (Hover)

Temporary.
Non-persistent.
Does not change URL state.

Hovering a pixel:

- Highlights the day.
- Displays contextual information.
- Highlights related persons.
- Highlights related tags.
- Shows relevant points on the map.

This is exploratory and ephemeral.

---

### B. Hard Highlight (Selection / Filtering)

Persistent.
Affects grid coloring.
Stored in URL state.
Composable.

Examples:

- Selecting a person highlights all days containing that person.
- Selecting a tag subtree highlights matching days.
- Applying a geographic filter highlights matching days.
- Selecting a derived view recolors the grid entirely.

Persistent filtering is a server-side concern.
The browser should request an already filtered grid projection instead of trying
to reproduce full-dataset filtering locally.

---

## 6. Grid Coloring Strategy

The grid is always colored according to a selected view mode.

Examples:

- Activity (default intensity-based heatmap)
- Travel
- Sports
- Party likelihood
- Custom derived view

Each mode defines a distinct color strategy.

The UI does not compute activity.
It consumes derived projections from the backend.

The UI also should not be the long-term execution site for complex persistent
filters such as geographic predicates, distance filters, or filename searches.

The grid must be able to fully re-render based on:

- active view mode
- selected filters
- time range

---

## 7. Bidirectional Linking

All contextual panels are bidirectionally linked to the grid.

Interaction matrix:

| Action              | Grid         | Map          | Persons      | Tags         |
|---------------------|--------------|--------------|--------------|--------------|
| Hover Pixel         | highlight    | show points  | highlight    | highlight    |
| Select Person       | recolor grid | show points  | active state | —            |
| Select Tag          | recolor grid | show points  | —            | active state |
| Select View Mode    | recolor grid | update       | update       | update       |

The grid is the primary projection.
Other panels react.

---

## 8. Derived Views

Derived analytics jobs may produce predefined views such as:

- Travel periods
- Sports activity
- Party probability
- High social density days

These are hardcoded derived jobs in the backend.

The UI provides a selector for switching between these modes.

Each mode controls how pixels are colored.

---

## 9. Timeline Entry Projection

The grid itself is not limited to Events.

Both `Event` and `Asset` contribute to the timeline.

The UI operates on a projection layer (TimelineEntry),
not directly on raw tables.

This avoids forcing Assets into Events.

---

## 10. Map Integration

The map is contextual, not dominant.

Default:
- empty or passive state.

On hover:
- show coordinates of that day only.

On filter:
- show all matching points.

Hover remains local once a bounded context range has been preloaded.
Persistent filter changes may trigger backend requests.

Map should not overwhelm the interface. If supported by the map view it should default to a subtle color grading, e.g. light grey colors if the whole UI has a light background or similarly dark grey colors in case of a dark UI theme.

---

## 11. Visual Philosophy

- Minimalistic pixels.
- No icons inside grid cells.
- Color-only encoding.
- Clean typography.
- Light mode by default, optionally dark mode later on.
- No visual noise.

The grid must remain readable at scale (10–30 years).

---

## 12. Out of Scope (v1)

- Mobile layout
- Complex zoom transitions
- Animated storytelling
- Overloaded dashboards
- Inline editing

---

## 13. Non-Negotiables

- The grid never disappears.
- Time is primary.
- Hover is lightweight.
- Filtering is powerful.
- Persistent filtering is server-side.
- Simplicity beats density.
