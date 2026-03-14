# R-024-02 - UI Shift to Server-Side Persistent Filtering

## Goal

Refactor the UI so persistent timeline filters are no longer applied locally
against the preloaded grid projection.

Instead, persistent filters should be sent to the backend, which returns an
already filtered grid projection. The client should keep only the local
interaction logic that benefits from immediate in-memory access, especially
hover behavior over a bounded visible context range.

## Dependencies

- `R-024-01`
- `R-012`
- `R-015`

## Reasoning

Today the UI treats persistent filters as a client-side projection problem. That
works only because the currently available filters are lightweight and because
the exploration response currently carries enough per-day metadata to support
local filtering heuristics.

That model breaks down as the product moves toward richer filtering such as:

- geographic bounding boxes and polygons
- distance-based location filters
- filename-based filters across the full asset set
- more advanced database-backed timeline predicates

Those filters must be evaluated against the full dataset and are best executed
on the server, often directly by the database.

Persistent filters also change relatively rarely. They are triggered by explicit
user actions such as button clicks, pill toggles, or URL-state changes. That
makes request/response updates acceptable.

Hover interaction is different. Hover must remain instant while moving over many
cells. For that reason, day-context data should still be preloaded for bounded
visible ranges and resolved locally during pointer movement.

The UI therefore should adopt this split:

- persistent filter application = server-side
- hover context consumption = client-side after bounded preload

## Scope

### Stop Client-Side Persistent Grid Filtering

Remove the current local filtering logic that derives filtered grid state from:

- per-day `personIds`
- per-day `tagPaths`
- local view-mode heuristics over the full preloaded grid

The UI should treat the server response as the source of truth for the filtered
grid state.

### Request Filtered Grid Data from the API

When persistent filters change, the UI should request the filtered grid payload
from the backend using the exploration endpoint defined in `R-024-01`.

At minimum, the client should send:

- `view_mode`
- selected person filters
- selected tag filters

The request flow should be structured so additional future filter parameters can
be added without reworking the client architecture.

### Keep Bootstrap and Grid Loading Separate

The UI should load:

1. bootstrap metadata once
2. filtered grid data whenever persistent filter state changes
3. bounded day-context ranges for hover/visible-window needs

Do not re-fetch bootstrap catalogs just because the grid filter changed unless
the backend contract explicitly requires that behavior.

### Keep Hover Local After Range Prefetch

The UI should continue to preload bounded `days/context` ranges and keep hover
highlighting local once the relevant range is available.

This includes:

- fast right-panel person/tag highlighting during hover
- fast map-point rendering for the currently hovered day
- no request-per-hover-cell behavior

### Revisit URL-State and Loading Semantics

Persistent filter state already participates in URL state. After this task,
those URL-backed filters must drive backend requests instead of only local
projection changes.

The UI should clearly handle:

- initial load from URL state
- loading transitions when persistent filters change
- stale response protection when multiple filter requests overlap
- empty filtered result sets

### Update UI Tests and Projection Logic

Tests should be updated so they verify the new responsibility split.

At minimum, coverage should assert:

- persistent filter changes trigger filtered grid requests
- grid rendering reflects server-filtered results rather than local filtering
- hover behavior continues to work from bounded cached day-context data
- no per-hover network dependency is introduced

## Out of Scope

- no redesign of filter controls
- no implementation of every future advanced filter type
- no requirement to redesign hover panels
- no requirement to eliminate all client-side derived UI projection logic

## Acceptance Criteria

- persistent grid filters are no longer executed by the browser over preloaded
  full-grid day summaries
- the UI requests filtered grid data from the backend whenever persistent
  filters change
- bootstrap metadata loading remains separate from grid-data loading
- hover interaction still relies on bounded preloaded context ranges and remains
  responsive during rapid pointer movement
- tests cover the new request flow and responsibility split

## Notes

The desired end state is not "server does everything" and "client does
nothing." The desired end state is a clean interaction model:

- the backend owns expensive and full-dataset persistent filtering
- the client owns immediate hover interaction over already loaded bounded data

That split is better aligned with the long-term roadmap than continuing to
stretch client-side filtering over increasingly complex derived summaries.
