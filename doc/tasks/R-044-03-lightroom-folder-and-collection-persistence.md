# R-044-03 - Lightroom Folder and Collection Persistence

## Goal

Extend the Lightroom catalog ingest so it persists both imported folder
hierarchy and Lightroom collection hierarchy during ingestion.

This task makes Lightroom the source of truth for the `Collections` tree while
also assigning each Lightroom-backed asset to its physical folder.

## Dependencies

- `R-040`
- `R-041-06`
- `R-044-01`

## Scope

### Persist Lightroom Folder Hierarchy

The Lightroom ingest should map catalog-backed file location information into
canonical `AssetFolder` rows.

Required outcomes:

- create or reuse folder rows per source and normalized path
- preserve parent-child hierarchy
- assign the correct leaf `folder_id` to each ingested asset
- keep repeated runs idempotent

### Persist Lightroom Collection Hierarchy

The ingest should persist Lightroom collections as canonical `AssetCollection`
rows.

The first-version contract should support:

- nested collection structure through `parent_id`
- stable collection identity through connector-scoped `external_id`
- normalized collection `path`
- explicit `collection_type` when the catalog distinguishes collection kinds

### Persist Collection Memberships

The ingest should create and reconcile `AssetCollectionItem` rows so one asset
can appear in multiple collections.

Required outcomes:

- repeated runs do not duplicate memberships
- new memberships are added correctly
- removed memberships are explicitly reconciled if the source no longer
  contains them

### Preserve Detail Metadata Needed Later

This task should preserve the existing Lightroom metadata payload required by
the future detail API, including named face-region data when it is already
available from the source ingest.

The goal is not to model face regions canonically here, but to keep the raw
detail data available on the asset for later single-photo loading.

### Add Connector Tests

The Lightroom ingest test suite should cover:

- repeated ingestion of the same folder and collection trees
- one asset in multiple collections
- nested collection persistence
- membership reconciliation on rerun
- assets receiving the correct `folder_id`

## Out of Scope

- no album API work
- no UI work
- no separate face-region table

## Acceptance Criteria

- Lightroom ingest persists canonical folders and collections during ingestion
- Lightroom assets receive the correct `folder_id`
- collection hierarchy and collection memberships are stored explicitly
- repeated runs reconcile collection memberships without duplication
- detail metadata needed for later single-photo loading remains available on
  the asset payload

## Notes

Folders and collections must remain separate structures even though both are
trees. One expresses physical provenance, the other expresses curated grouping.
