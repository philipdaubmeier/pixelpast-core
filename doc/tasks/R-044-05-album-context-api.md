# R-044-05 - Album Context API

## Goal

Expose the stable right-column context for a selected folder or collection.

This task provides the aggregated people, tag, and map context that remains
visible while the user browses thumbnails inside one album selection.

## Dependencies

- `R-015`
- `R-024-02`
- `R-044-04`

## Scope

### Define A Stable Album Context Contract

Add an explicit API contract that returns album context for a selected folder
or collection under the current global filters.

The response should support the right-column baseline state:

- people aggregates
- tag aggregates
- map points or map bounds as appropriate for the current UI contract
- total asset counts and related summary information

### Keep Hover Highlighting Client-Side

This API should define the stable album context only.

Required direction:

- no server request on thumbnail hover
- thumbnail hover highlights matching people and tags locally inside the
  already loaded context payload
- the context response stays structurally stable while the user moves across
  thumbnails

### Support Folder And Collection Selections

The contract should work for:

- leaf folders
- parent folders aggregated across descendants
- collections
- nested parent collections if the UI later chooses to allow aggregate
  collection selection

### Add Backend Tests

The backend test suite should cover:

- folder context responses
- collection context responses
- deterministic ordering of people and tags
- empty-context behavior
- supported filter application

## Out of Scope

- no single-photo detail payload
- no thumbnail-hover API route
- no UI rendering work

## Acceptance Criteria

- a dedicated album-context REST contract exists
- the contract returns stable right-column context for folder and collection
  selections
- the design explicitly keeps thumbnail hover highlighting client-side
- deterministic ordering and empty states are covered by tests

## Notes

This task is intentionally similar in role to the day-context API, but the
projection is album-selected and asset-centric rather than day-selected and
timeline-centric.
