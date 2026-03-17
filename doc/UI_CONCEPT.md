# PixelPast - UI Concept

## 1. Intuition

PixelPast is not a dashboard.
It is not a CRUD interface.
It is a visual exploration instrument.

The UI exists to make time explorable.
projections.

The calendar grid is not a component.  
It is the product.

Everything else in the interface exists to contextualize, filter, enrich, or reinterpret the grid.
If a UI decision weakens the clarity of chronological exploration, it is the wrong decision.

---

## 2. Core Design Principles

1. Calendar-first.
2. All years visible at once.
3. Exploration over editing.
4. Hover for context.
5. Selection for filtering.
6. Visual simplicity over density.
7. Desktop-first.

---

## 3. Main Views

PixelPast should expose a small number of primary exploration modes.

The first two are:

- `Day Grid`
- `Social Graph`

These are not variations of one widget.
They are different projections over the same underlying personal-history data.

### `Day Grid`

Purpose:

- explore time continuously across years
- recolor history through different grid views
- inspect hovered day context

### `Social Graph`

Purpose:

- explore person co-occurrence across assets
- reveal clusters, hubs, and bridges between groups
- inspect social topology without forcing it into a calendar layout

---

## 4. Shared Shell

The app shell should stay stable while the main view changes.

Top bar structure:

```text
+---------------------------------------------------------------+
| Logo | Day Grid | Social Graph | Global Filters              |
+---------------------------------------------------------------+
| Grid Views (only when Day Grid is active)                     |
+---------------------------------------------------------------+
```

The first row is app-level.
The second row is view-level and appears only when needed.

This distinction matters because the user is not only recoloring a grid anymore.
The user is switching between different exploration modes.

---

## 5. Day Grid Mode

When `Day Grid` is active, the layout remains split:

```text
+---------------------------------------------------------------+
| Top Bar                                                       |
+-------------------------------+-------------------------------+
| Year Grid Stack               | Persons                      |
|                               | Tags                         |
|                               | Map                          |
+-------------------------------+-------------------------------+
```

Behavior:

- all years remain visible in one stacked chronology
- grid views recolor the same temporal surface
- right-side panels react to hover and persistent filters
- timeline hover stays lightweight and ephemeral

The grid remains the primary surface inside this main view.

---

## 6. Social Graph Mode

When `Social Graph` is active, the layout may change completely:

```text
+---------------------------------------------------------------+
| Top Bar                                                       |
+---------------------------------------------------------------+
|                                                               |
|                  Social Graph Surface                         |
|                                                               |
+---------------------------------------------------------------+
```

Optional overlays such as legends, summaries, or graph-local controls may be
added if they remain visually quiet.

The social graph should not be forced into the day-grid split layout if that
hurts readability.

---

## 7. Global Filters

Persons, tags, and a future date range belong in the top bar as persistent
global controls.

Rules:

- they remain visible across main-view switches
- their state survives navigation and refresh
- the app must be explicit about whether the active main view currently applies
  each filter dimension

The important principle is shared ownership of filter state, not silent reuse
of one projection's semantics in another projection.

---

## 8. Grid Views

The controls currently called `view modes` should be renamed conceptually to
`grid views`.

Examples:

- `activity`
- `calendar`
- `vacation`

These are not top-level destinations.
They are coloring strategies within the `Day Grid` main view.

Therefore they should:

- appear only when `Day Grid` is active
- look visually subordinate to the main-view buttons
- never compete with `Day Grid` versus `Social Graph` navigation

---

## 9. Interaction Model

There are three interaction layers:

### A. Main-View Switch

Persistent.
Changes the active projection surface.

Examples:

- switch from `Day Grid` to `Social Graph`
- preserve global filters while changing the layout and data request path

### B. Hover

Temporary.
Non-persistent.
Never changes URL state.

Examples:

- hover a day cell
- hover a person node
- hover a graph link

### C. Selection and Filtering

Persistent.
Stored in URL state where appropriate.
Defines the durable exploration frame.

Examples:

- select persons
- select tags
- choose a grid view

Persistent filtering should remain a server-side concern whenever the active
projection depends on server-evaluated data constraints.

---

## 10. Social Graph Semantics

The first social graph should be built from person co-occurrence on assets.

Conceptually:

- nodes are persons
- node size reflects occurrence count, preferably logarithmically
- links connect persons who appear on the same asset
- link weight reflects repeated co-occurrence
- the layout is force-directed with repulsion, collision handling, and weighted
  spring forces

This is a projection of social proximity, not a ground-truth relationship model.
The UI should present it as exploratory evidence, not as an authoritative social
ontology.

---

## 11. Resource and Lifecycle Principle

Main views should not all remain live at once.

Best practice here is:

- preserve durable state across main-view switches
- cache reusable fetched data where helpful
- unmount heavy view runtimes when inactive

For `Social Graph`, that means:

- stop the force simulation when leaving the view
- remove graph-local listeners and animation work
- remount and resume from data when returning

The expensive runtime should go away.
The durable exploration context should remain.

---

## 12. Visual Philosophy

- minimal shell chrome
- clear hierarchy between main-view navigation and secondary controls
- no visual noise inside the day grid
- clean typography
- light mode by default, optionally dark mode later

The day grid must remain readable at scale.
The social graph must remain legible as a topology view rather than collapsing
into decorative chaos.

---

## 13. Out of Scope

- mobile layout
- graph editing
- persisted manual graph layouts
- overloaded dashboards
- inline editing

---

## 14. Non-Negotiables

- chronology remains the product backbone
- the day grid remains the default main view
- global filters stay visible across main-view switches
- grid views are not top-level navigation
- hover stays lightweight
- persistent filtering remains explicit
- simplicity beats density
