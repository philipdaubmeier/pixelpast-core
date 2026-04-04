# R-048-02 - Large Album Grid Pagination and Viewport-Context Loading

## Goal

Introduce pragmatic pagination for very large album selections without making
normal folder browsing feel slower.

This task should optimize the album grid for cases such as:

- parent-folder aggregation across a year
- root-node selections
- unusually large imported folders

The intended behavior is not "tiny pages and constant churn".
The intended behavior is:

- large pages
- few requests
- scroll-stable layout
- deferred loading only for ranges the user actually reaches

## Dependencies

- `R-048-01`

## Scope

### Add Large-Page Album Listing Pagination

Album asset listing routes should support explicit pagination.

Required direction:

- default page size is `1000`
- the API may expose `limit` and `offset`, or an equivalent explicit page
  contract
- server ordering remains stable across pages
- the route returns enough metadata for the client to know the total result size
  and the loaded range

The page size should intentionally stay large.

Rationale:

- common folders with a few hundred assets should still load in one request
- pagination should mainly activate as protection for very large aggregate
  selections
- the system should avoid replacing one expensive query with many medium-sized
  queries on ordinary album nodes

### Keep Grid Scroll Geometry Stable

The UI should reserve placeholder slots for unloaded asset ranges so the grid
keeps its real total height and the scrollbar behaves correctly from the start.

Required outcomes:

- unloaded pages keep their spatial slot in the grid
- scrolling does not jump when a page resolves
- already loaded pages keep their rendered position
- the user can scrub through a large selection without the layout collapsing

This task is about scroll-stable progressive loading, not a fake infinite list
that only appends at the bottom.

### Trigger Page Loads From Viewport Reachability

The client should not eagerly load every page for a large selection.

Required direction:

- the first page loads immediately after explicit album selection
- additional pages load only when their reserved range is approached or becomes
  visible through scrolling
- page loading should use a short dwell threshold before firing for a newly
  visible range

Preferred initial threshold:

- around `1` second of visibility or near-visibility

The threshold exists to avoid noisy request churn during fast scrolling.

### Paginate Hover Context Alongside Asset Pages

The current album context payload contains per-asset hover links for the loaded
selection.

For large selections, that should no longer require one giant all-assets
context response.

Required direction:

- hover-context payload is page-aligned with the asset listing
- the first visible page gets its hover-context data together with or directly
  after the asset page
- later pages load their hover-context payload only when the corresponding page
  is actually approached
- hover interactions remain fully client-side once the page-local hover context
  has been loaded

This task should keep the distinction clear:

- stable selection-level summaries may remain separately loaded
- per-asset hover links should scale with paged asset ranges

### Preserve A Stable Selection-Level Context Layer

Pagination should not break the right-column model.

Recommended split:

- selection-level context summary endpoint
  - selected node metadata
  - person groups
  - aggregate people
  - aggregate tags
  - aggregate places
  - summary counts
- page-level hover-context endpoint or embedded page payload
  - only per-asset links needed for hover highlighting inside the loaded page

This avoids forcing the UI to reload the full right-column summary whenever an
additional asset page becomes visible.

### Avoid Over-Fragmenting The API

This task should not introduce a highly abstract transport model that is more
complex than the product need.

Preferred direction:

- one paged asset listing contract
- one compatible page-scoped hover-context contract, or one combined page payload
- stable selection-summary contract kept separate if needed

The result should stay explicit and easy to cache on the client.

## Out of Scope

- no reduction of page size below the large-page strategy described here
- no image-detail payload changes
- no album-tree pagination
- no speculative prefetch of many future pages by default

## Acceptance Criteria

- album asset listing supports large-page pagination with a default size of
  `1000`
- server ordering and page boundaries are deterministic
- the client reserves placeholder space for unloaded asset ranges so scrollbar
  behavior matches total result size
- the first page loads immediately after explicit selection
- later pages load only after viewport reachability plus a short dwell delay
- per-asset hover-context data is paged alongside the asset pages
- selection-level context remains stable and does not require full reload on
  every additional page fetch
- backend and UI tests cover page boundaries, empty tail pages, and viewport-
  triggered loading behavior

## Notes

This task should optimize for the observed folder shape:

- many normal selections are a few hundred photos
- the worst cases are aggregate selections over very large subtrees

That is why the page size should stay deliberately high.
The goal is not to paginate everything aggressively.
The goal is to cap pathological cases while preserving one-shot loads for
ordinary folders.
