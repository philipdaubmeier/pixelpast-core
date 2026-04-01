# R-044-06 - Photo Detail API with Metadata and Face Regions

## Goal

Expose a dedicated single-photo detail payload for the selected asset in the
photo-album view.

This task provides the lazy-loaded detail contract used when the user moves
from album browsing into single-asset focus.

## Dependencies

- `R-043-05`
- `R-044-04`

## Scope

### Define The Selected-Asset Detail Contract

Add an explicit API route for loading one selected asset with detail fields
that are too heavy or too specific for the album grid payload.

The first-version response should support:

- canonical asset identity
- title, caption, or description fields when available
- capture timestamp and location fields
- camera and lens details when available
- exposure metadata such as aperture, shutter speed, focal length, and ISO
- tags and people already associated with the asset
- media URLs needed by the UI to open the original image

### Read Rich Detail From Asset Metadata Payloads

The detail projection may read rich photo metadata from the stored asset
metadata or raw payload rather than from new top-level canonical columns.

Required direction:

- keep the API mapping explicit
- return normalized response fields to the client
- avoid leaking opaque raw metadata blobs directly through the endpoint

### Return Face Regions From Stored Metadata

This task should expose named face-region overlays directly from the persisted
asset metadata payload.

The first increment should:

- return face regions only in the single-photo detail payload
- support optional overlay rendering in the UI
- exclude unconfirmed or unnamed regions if the source payload distinguishes
  them

### Add Backend Tests

The backend test suite should cover:

- successful detail response shape
- assets without optional camera metadata
- assets without face regions
- deterministic field mapping from stored metadata payloads

## Out of Scope

- no face-region editing
- no separate canonical face-region schema
- no binary media delivery implementation beyond linking to the existing media
  routes

## Acceptance Criteria

- a dedicated single-photo detail REST contract exists
- the contract returns normalized metadata fields without leaking raw blobs
- face regions are exposed from stored asset metadata for selected assets
- empty optional metadata cases behave deterministically

## Notes

This task should keep the heavy detail payload off the album grid hot path.
Thumbnail browsing stays light; deep detail loads only when the user asks for
one asset.
