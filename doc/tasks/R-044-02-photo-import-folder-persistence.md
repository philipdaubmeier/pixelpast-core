# R-044-02 - Photo-Import Folder Persistence

## Goal

Extend the photo-import ingest so it persists imported folder hierarchy during
ingestion and assigns each imported asset to its canonical folder.

This task makes the physical `Folders` tree real for the plain photo-import
connector.

## Dependencies

- `R-020`
- `R-041-06`
- `R-044-01`

## Scope

### Persist Folder Hierarchy During Photo Import

The photo-import connector should derive folder hierarchy from the discovered
filesystem paths it already processes.

Required outcomes:

- create or reuse canonical `AssetFolder` rows for the source
- preserve parent-child relationships for the discovered hierarchy
- normalize and persist folder `path`
- keep repeated runs idempotent

### Assign `asset.folder_id`

Every imported photo asset that participates in folder browsing should be
written with the canonical leaf-folder foreign key.

The connector should:

- assign the correct leaf folder on initial import
- preserve or update the assignment on repeated runs
- avoid creating duplicate folder rows for the same source and path

### Keep Existing Asset Identity Rules Stable

This task must not redesign asset identity.

Required constraints:

- `external_id` remains the photo-import asset identity
- existing asset upsert semantics stay intact
- `folder_id` is additional navigation structure, not a replacement for asset
  identity

### Add Connector Tests

The photo-import ingest test suite should cover:

- repeated ingestion of the same folder tree
- sibling folders under one year folder
- parent-folder creation before leaf-folder assignment
- existing assets gaining `folder_id` on rerun or fill-in paths

## Out of Scope

- no collection persistence in the photo-import connector
- no album API work
- no UI work

## Acceptance Criteria

- photo-import ingest persists canonical folder rows during ingestion
- photo-import assets receive the correct `folder_id`
- repeated runs do not duplicate folders or break folder assignments
- connector tests cover hierarchy creation and idempotent reruns

## Notes

The key architectural rule is that folder creation belongs in ingest, not in a
later derive step. The connector already owns the source filesystem context and
should remain the source of truth for that mapping.
