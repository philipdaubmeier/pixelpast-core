# R-048 - Photo Album Performance Simplification

## Goal

Make the `Photo Album` view responsive for large libraries by simplifying the
read model semantically before reaching for low-level database tuning.

The direction of this series is:

- narrow the album API surface to filters that are meaningful per read shape
- stop implicit heavy album loads on initial view entry
- preserve useful album state without forcing unnecessary reloads
- prefer selection-scoped SQL and derived rows over Python-side full scans

This series should treat performance as a product-semantics problem first and
only then as an indexing problem.

## Dependencies

- `R-044`
- `R-047`

## Scope

This task series covers four connected concerns:

- API-surface simplification for album tree, grid, and context reads
- explicit lazy loading semantics for the album center column
- in-memory retention of useful album view state across main-view switches
- query-shape hardening for large album selections

### Separate Tree Navigation From Selected-Node Filtering

The current album API allows almost every filter dimension to flow into almost
every album endpoint.

That makes the contract broader than the actual product behavior needs and
encourages overly generic repository code.

This series should instead keep the read shapes distinct:

- tree navigation
  - structural navigation plus person-group relevance
- selected-node asset listing
  - thumbnail browsing within one selected folder or collection
- selected-node stable context
  - people, tags, and map aggregates for that selected result set
- single-asset detail
  - lazy metadata and face-region loading for one selected asset

### Simplify Before Tuning

The first performance step should not be a blind sweep of additional indexes.

Instead, the series should remove unnecessary filtering paths and stop
recomputing broad result sets that the user does not actually need on screen.

Only after the final request shapes are stable should index additions or query
plan tuning be evaluated.

### Keep Large-Album Behavior Explicit

Large imported libraries make three product-level constraints important:

- the album view must not auto-open a massive root node
- switching away from the album view should not discard useful local state
- empty filtered results inside a selected album node are valid outcomes and
  should be shown explicitly rather than avoided by silent reselection

### Push Work Down To The Real Selection Boundary

Album reads should not start by loading nearly all assets and filtering them in
Python.

The intended direction is:

- narrow to the selected folder subtree or collection subtree first
- apply the remaining meaningful filters only within that bounded candidate set
- reuse derived relevance rows where they already exist

## Provisional Subtasks

- `R-048-01` - Album API surface simplification and selection-scoped loading
- `R-048-02` - Large-album grid pagination and viewport-triggered context loading
- `R-048-03` - Album view state retention and in-memory request reuse
- `R-048-04` - Album tree and read-model query hardening

## Out of Scope

- no generic "support every global filter everywhere" contract expansion
- no blind index sweep as the primary optimization tactic
- no attempt to merge folders and collections into one generic navigation tree
- no silent fallback that auto-selects another node when a filtered selection is
  empty

## Acceptance Criteria

- a focused task series exists for album performance simplification
- the series starts from API and product semantics rather than only from schema
  tuning
- the series makes initial album loading, state retention, and large-selection
  behavior explicit
- the series leaves room for later index work only after request shapes are
  stable

## Notes

The current album implementation already keeps single-asset detail off the hot
path, which is good.

The biggest remaining cost is not one specific table size but the mismatch
between:

- what the user actually needs to see immediately
- what the API currently allows and the repository therefore computes
