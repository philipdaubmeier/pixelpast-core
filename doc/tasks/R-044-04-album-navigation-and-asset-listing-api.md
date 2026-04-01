# R-044-04 - Album Navigation and Asset-Listing API

## Goal

Expose the navigation trees and album asset listings needed by the photo-album
main view through explicit REST contracts.

This task provides the backend surface for the left column and the center
thumbnail grid.

## Dependencies

- `R-024-02`
- `R-043-04`
- `R-044-01`
- `R-044-02`
- `R-044-03`

## Scope

### Expose Folder And Collection Navigation Trees

Add explicit API contracts for loading:

- the `Folders` tree
- the `Collections` tree

The implementation may use separate endpoints or one bootstrap response, but
the contract must keep the two trees semantically distinct.

Required outcomes:

- deterministic node ordering
- explicit node identity and parent relationships
- counts or summary fields needed by the UI tree presentation

### Expose Album Asset Listings

Add API routes for loading the assets contained in a selected folder or
collection.

The listing contract should support:

- selection by folder id
- selection by collection id
- aggregate listing for parent nodes across descendants
- stable ordering suitable for thumbnail browsing
- thumbnail URLs derived from the public media-delivery contract

### Apply Global Persistent Filters

Album listings should participate in the same persistent filter system used by
the rest of the app.

The first-pass backend contract should explicitly define which filter
dimensions are supported for album listings and how they affect:

- node counts
- asset result sets
- empty states

Unsupported filter dimensions must be explicit rather than silently ignored.

### Add Backend Tests

The backend test suite should cover:

- folder-tree response shape
- collection-tree response shape
- parent-node aggregate listing behavior
- deterministic asset ordering
- supported filter behavior
- empty album behavior

## Out of Scope

- no right-column context payload yet
- no single-photo detail payload yet
- no UI rendering work

## Acceptance Criteria

- explicit REST contracts exist for folder and collection tree loading
- explicit REST contracts exist for folder and collection asset listings
- parent-node aggregate browsing is supported
- album listings return thumbnail-oriented asset data suitable for the center
  grid
- supported global filter behavior is defined and tested

## Notes

This task should keep navigation loading and asset listing separate from the
later context and detail APIs. The album view needs distinct read paths for the
tree, the grid, the right-column context, and the selected asset.
