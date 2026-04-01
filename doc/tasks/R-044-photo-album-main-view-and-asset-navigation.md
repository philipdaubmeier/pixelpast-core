# R-044 - Photo Album Main View and Asset Navigation

## Goal

Introduce `Photo Album` as a third main exploration view alongside `Day Grid`
and `Social Graph`.

This view should give PixelPast a photo-centric drill-down surface without
breaking the existing chronology-first product shape:

- `Day Grid` remains the primary temporal projection
- `Photo Album` becomes the asset-centric deep-dive view
- persistent filters remain global and survive main-view switches
- shared people, tag, and map controls keep one consistent interaction model

The first increment should make imported folder hierarchy and Lightroom
collections first-class navigation structures for browsing large photo sets.

## Dependencies

- `R-020`
- `R-024-02`
- `R-035`
- `R-040`
- `R-043`

## Scope

This task series covers five layers:

- canonical schema support for folder and collection navigation
- ingest-time persistence for photo-import folders and Lightroom folders and
  collections
- REST endpoints for album trees and album asset listing
- REST endpoints for album context and single-photo detail loading
- UI delivery of the new three-column photo-album main view

### Introduce Two Explicit Navigation Trees

The left column should expose two separate tree structures:

- `Folders`
  - imported physical hierarchy as preserved by the ingest source
- `Collections`
  - semantic Lightroom groupings where one asset may belong to multiple
    collections

These trees should be modeled and loaded separately. They serve different
product purposes and should not be collapsed into one generic table or one
generic API contract.

### Keep The Center Column Asset-Centric

Selecting a folder or collection should load an album-style asset result set in
the center column.

The initial album contract should support:

- thumbnail-grid browsing
- parent-node aggregate browsing across descendants
- persistent-filter application from global app state
- transition into single-asset focus without hiding the side columns

### Keep The Right Column Stable

The right column should reuse the same people, tag, and map controls already
established in the day-grid experience.

The view contract should preserve the existing PixelPast interaction model:

- hover = temporary highlight only
- click = persistent filter add or remove

Hovering a thumbnail must not trigger layout jumps or server-backed panel
replacement. The stable album context is loaded for the selected node, while
thumbnail hover only highlights matching elements locally inside that context.

### Load Heavy Detail Only For A Selected Asset

Single-photo detail should be loaded lazily when the user selects an asset.

That detail payload should support:

- larger image rendering in the center column
- metadata display in the right column
- face-region overlays loaded from the persisted asset metadata payload

This series should not introduce a separate canonical face-region table.

### Keep Folder And Collection Persistence In Ingest

Folder and collection structures should be created during source ingestion, not
in a later derive job.

Required direction:

- photo-import ingest persists physical folders and `asset.folder_id`
- Lightroom ingest persists physical folders, collections, and
  collection-membership rows
- existing database contents gain a fill-in path so already imported assets can
  participate in the new album view

## Subtasks

- `R-044-01` - Album navigation schema and fill-in foundation
- `R-044-02` - Photo-import folder persistence
- `R-044-03` - Lightroom folder and collection persistence
- `R-044-04` - Album navigation and asset-listing API
- `R-044-05` - Album context API
- `R-044-06` - Photo detail API with metadata and face regions
- `R-044-07` - Photo album main-view UI

## Out of Scope

- no metadata editing or Lightroom write-back
- no user-authored collection creation inside PixelPast
- no separate canonical face-region table in this increment
- no album-specific filter model separate from the existing global filters
- no slideshow mode, bulk selection, or export workflow
- no attempt to infer semantic albums from tags, dates, or places yet

## Acceptance Criteria

- a task series exists for adding `Photo Album` as a first-class main view
- the series explicitly separates imported folder navigation from collection
  navigation
- the series defines canonical support for `AssetFolder`,
  `AssetCollection`, `AssetCollectionItem`, and `Asset.folder_id`
- the series includes a fill-in path for already ingested database contents
- the series extends both photo-import and Lightroom ingestion rather than
  pushing folder and collection creation into derive jobs
- the series defines explicit API contracts for:
  - folder and collection tree loading
  - album asset listing
  - stable album context for the right column
  - single-photo detail loading
- the series defines a UI task that keeps the three-column Lightroom-like
  layout while reusing shared controls and global filters

## Notes

This series should treat the photo album as a separate projection over the same
canonical corpus, not as a parallel mini-application. The core shape should
stay consistent with the rest of PixelPast:

- shared filters and controls at the app level
- explicit read contracts per projection
- chronology still anchored by the day grid
