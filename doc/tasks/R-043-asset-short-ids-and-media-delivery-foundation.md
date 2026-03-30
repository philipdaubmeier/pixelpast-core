# R-043 - Asset Short IDs and Media Delivery Foundation

## Goal

Introduce a stable public media identifier for canonical assets and a fixed
thumbnail-delivery model optimized for browsing-heavy photo exploration.

The first increment should make PixelPast efficient for the hot path of media
exploration:

- browsing folders and timelines with large thumbnail grids
- scrolling through hundreds of assets in short succession
- opening the occasional original image at full size

The series should explicitly optimize thumbnail delivery for low per-request
overhead while keeping original-file delivery correct, source-aware, and able
to preserve the original filename in responses.

## Dependencies

- `R-020`
- `R-025`
- `R-028-03`
- `R-040`
- `R-041-06`

## Scope

### Introduce Stable Public Asset Short IDs

Every canonical asset should gain a stable short public identifier used by the
media-delivery surface.

The first-version contract is:

- one globally unique `Asset.short_id`
- fixed length of 8 characters
- Base58 alphabet excluding visually ambiguous characters:
  - `0`
  - `O`
  - `I`
  - `l`
- once assigned, the short id remains immutable

This identifier should become the public media key for both thumbnail and
original-image delivery.

### Optimize The Browsing Path For Thumbnail Delivery

Thumbnail delivery should be designed around filesystem hits rather than around
database reads on every request.

The repository should gain exactly three fixed thumbnail renditions:

- `h120`
- `h240`
- `q200`

All thumbnails should be stored as WebP files.

No generic on-the-fly resize API should be introduced in this series.

### Define Fixed Thumbnail Semantics

The three supported renditions should have explicit image-processing rules:

- `h120`
  - output height is 120 pixels
  - width scales proportionally
  - source images wider than `3:1` are center-cropped horizontally down to
    `3:1` before scaling
- `h240`
  - output height is 240 pixels
  - width scales proportionally
  - source images wider than `3:1` are center-cropped horizontally down to
    `3:1` before scaling
- `q200`
  - the largest possible centered square crop is taken from the source image
  - output size is `200x200`

These rendition rules should be fixed in code for v1.

### Separate Thumbnail And Original Delivery Paths

The media surface should be split into two intentionally different access
patterns:

- thumbnails:
  - short-id based
  - fixed rendition routes
  - optimized for filesystem hits
  - optional lazy generation on cache miss
- originals:
  - short-id based
  - resolved through the database and source-specific file provenance
  - returned with `Content-Disposition` containing the original filename

### Require Explicit Thumbnail Storage Configuration

Asset ingestion should not proceed unless a fixed thumbnail-storage root has
been configured for the running PixelPast instance.

This series should define a dedicated runtime setting for the thumbnail root and
require all asset-ingest entrypoints to fail fast when it is missing or
invalid.

### Keep Authentication And Signed Media URLs Out Of Scope

This first increment should not introduce:

- login-aware access control
- signed thumbnail URLs
- signed original-media URLs
- per-user media authorization

The goal is to establish the storage and delivery contract first.

## Out of Scope

- no ZIP export of full folders in this series
- no user-login integration
- no generic media transformation service with arbitrary width or height
- no video transcoding or non-image preview pipeline
- no secret or signature-based media authorization yet

## Suggested Subtasks

- `R-043-01`
  - add the canonical `Asset.short_id` schema and backfill existing rows
- `R-043-02`
  - generate and preserve short ids across all asset write paths and require
    thumbnail-root configuration before asset ingest
- `R-043-03`
  - add a derive job that precomputes fixed WebP thumbnail renditions with
    force and missing-only behavior
- `R-043-04`
  - expose short-id-based thumbnail delivery routes optimized for filesystem
    hits with lazy fallback generation on cache miss
- `R-043-05`
  - expose short-id-based original-media delivery with database-backed asset
    resolution and original filename headers

## Acceptance Criteria

- a task series exists for short-id-based media delivery
- the series explicitly defines the `8`-character Base58 public asset id
  contract
- the series explicitly limits thumbnail variants to `h120`, `h240`, and
  `q200`
- the series explicitly requires WebP output for all thumbnails
- the series explicitly requires a configured thumbnail root before asset
  ingestion can run
- the series explicitly separates thumbnail delivery from original-file
  delivery
- the series explicitly states that thumbnail requests should avoid database
  work on cache hits
- the series explicitly keeps auth and signed URLs out of scope for this first
  increment

## Notes

This series is intentionally optimized for the exploration use case rather than
for original-file download frequency. The design target is that PixelPast can
serve large scrolling thumbnail grids cheaply while still resolving originals
correctly when the user opens an asset.
