# R-044-01 - Album Navigation Schema and Fill-In Foundation

## Goal

Extend the canonical asset model with explicit folder and collection
structures, and provide a fill-in path for already ingested data.

This task establishes the storage layer required by the later album APIs and
UI.

## Dependencies

- `R-044`

## Scope

### Add Canonical Folder Support

Introduce a canonical `AssetFolder` structure for imported physical folder
hierarchy.

The first-version contract should include:

- hierarchical rows with `parent_id`
- source ownership through `source_id`
- stable display name in `name`
- normalized hierarchy path in `path`

`AssetFolder` intentionally should not gain an `external_id` or `created_at`
field in this increment.

### Add Canonical Collection Support

Introduce canonical collection storage for Lightroom-style semantic groupings.

The first-version contract should include:

- hierarchical rows with `parent_id`
- source ownership through `source_id`
- stable display name in `name`
- normalized hierarchy path in `path`
- connector-scoped ingest identity in `external_id`
- explicit classification in `collection_type`
- optional connector-owned extension data in `metadata`

### Add Asset Association Columns And Tables

The canonical asset layer should support both navigation models:

- `Asset.folder_id`
  - nullable for assets that do not participate in imported folder browsing
- `AssetCollectionItem`
  - explicit `n:m` association between assets and collections
  - uniqueness on `(collection_id, asset_id)`

The task should define the needed indexes and foreign keys for practical album
queries.

### Add Persistence And Domain Boundaries

Update the domain and persistence layers so folder and collection structures are
first-class repository concerns.

Required outcomes:

- domain entities exist for folders and collections
- ORM mappings exist for folders, collections, and collection items
- repository contracts can read and write album-navigation structures
- asset persistence understands `folder_id`

### Provide A Fill-In Path For Existing Data

Existing repositories should gain a fill-in path that hydrates the new schema
from data already present in the database wherever possible.

The fill-in direction should be:

- build folder rows and `asset.folder_id` from persisted asset path metadata
  already captured by photo-import and Lightroom asset rows
- build collection rows and collection memberships from persisted Lightroom raw
  payload or metadata when the necessary collection identity is already stored
- avoid requiring a full source re-import when the needed source data is
  already present locally in the database

If some historic rows genuinely lack enough persisted source information, the
task should define explicit fallback behavior rather than silently inventing
folders or collections.

## Out of Scope

- no ingest-service changes yet
- no API endpoints yet
- no UI work yet
- no face-region schema extraction from asset metadata

## Acceptance Criteria

- canonical schema support exists for `AssetFolder`, `AssetCollection`,
  `AssetCollectionItem`, and `Asset.folder_id`
- `AssetFolder` omits `external_id` and `created_at`
- `AssetCollection` includes a stable connector-scoped `external_id`
- repository and ORM layers expose the new structures explicitly
- a fill-in path exists for already ingested assets and Lightroom collection
  data where the source information is already persisted

## Notes

This task should keep the storage contract explicit and queryable. Folder and
collection trees are navigation primitives for the product, not arbitrary JSON
fragments hidden inside `Asset.metadata`.
