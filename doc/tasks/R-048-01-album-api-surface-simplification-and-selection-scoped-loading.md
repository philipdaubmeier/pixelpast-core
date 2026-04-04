# R-048-01 - Album API Surface Simplification and Selection-Scoped Loading

## Goal

Reduce the album hot path by simplifying filter semantics and aligning the API
with the intended browsing behavior for large photo libraries.

This task should make the contract closer to Lightroom-like navigation:

- people, tags, and later location filters affect the currently selected album
  node
- person-group filters affect album tree visibility
- entering the album view does not implicitly load a large root result set

## Dependencies

- `R-044-04`
- `R-044-05`
- `R-044-07`
- `R-047-04`

## Scope

### Narrow The Folder And Collection Tree Contracts

`/albums/folders` and `/albums/collections` should stop accepting the full
album filter surface.

Required direction:

- tree routes accept `person_group_ids`
- tree routes reject `person_ids`
- tree routes reject `tag_paths`
- tree routes reject all location filters
- tree routes reject `filename_query`
- tree node counts remain structural summaries instead of person or tag filtered
  counts

The tree should remain structurally stable when people, tags, or location
filters are active elsewhere in the app.

Only the selected person-group filter may exclude album nodes from the tree.

### Keep Selected-Node Filtering Local

Album asset listing and stable context reads should apply only to the current
selected folder or collection.

Required direction:

- `person_ids` constrain only the selected node result set
- `tag_paths` constrain only the selected node result set
- location filtering belongs only on selected-node routes once album location
  filtering is implemented for real
- `person_group_ids` stop constraining selected-node listings and contexts

This task should keep the semantics explicit:
person-group filtering is a navigation concern, not a second asset-list
filtering system.

### Remove Unused Album-Wide Filename Filtering

`filename_query` currently adds contract and repository complexity without a
real album-view control using it.

Preferred direction for this increment:

- remove `filename_query` from album routes
- remove it from album response metadata and tests

If filename search becomes a real album feature later, it should return in a
dedicated task with a concrete UI affordance and measured need.

### Stop Implicit Default Album Selection

Entering the album view should not auto-pick the first folder or collection
with assets.

Required outcomes:

- the initial album center column remains empty
- the UI shows an explicit prompt to select a folder or collection
- listing and context loading start only after explicit user selection
- if a tree filter invalidates the current selection, the UI falls back to
  `no selection` instead of silently opening another node

### Keep Empty Filter Results Honest

When a selected folder or collection contains no assets matching the active
people, tag, or later location filters, the selection should remain active.

The result should be:

- empty grid
- stable selection label
- explicit empty-state message

This task should not hide emptiness by altering the selection automatically.

### Make The Repository Follow The Narrower Contract

The repository implementation should stop starting from the full asset corpus
for album hot-path reads.

Required direction:

- tree reads use structural folder or collection rows plus persisted
  person-group relevance rows
- selected-node listing reads first narrow to the chosen folder subtree or
  collection subtree
- remaining filters are applied only inside that candidate set
- hot-path reads should not rely on loading all assets and post-filtering them
  in Python

This task does not require every later optimization at once, but it should not
keep the current generic full-scan shape under a narrower API contract.

## Out of Scope

- no cross-view in-memory caching yet
- no grid pagination or viewport virtualization yet
- no new location filter implementation in this increment
- no album-specific search box or filename-search UX

## Acceptance Criteria

- album tree routes accept only `person_group_ids`
- album tree routes reject person, tag, location, and filename filters with
  explicit errors
- album listing and context reads keep people and tag filters local to the
  selected node
- person-group filtering no longer changes selected-node listing semantics
- album view opens without implicit folder or collection selection
- invalidated selection falls back to `no selection`, not silent reselection
- empty selected-node results remain visible as explicit empty states
- backend and UI tests cover the new contract and loading behavior

## Notes

This task intentionally changes semantics before adding caching or pagination.

That sequence matters because later client-side caching should key off a
smaller, clearer request model instead of preserving an overly broad one.
