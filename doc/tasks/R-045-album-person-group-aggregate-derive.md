# R-045 - Album Person Group Aggregate Derive

## Goal

Introduce a dedicated derive job that materializes person-group relevance for
album folders and album collections.

The job should scan canonical album structures together with canonical
asset-to-person evidence and produce explicit derived associations that answer
both directions efficiently:

- which person groups are relevant for one folder or collection
- which folders or collections are relevant for one person group

The important boundary for this task is:

- folders and collections remain separate album structures
- canonical `Asset`, `Person`, `PersonGroup`, and membership rows remain the
  source of truth
- derived relevance links are materialized into explicit relational tables
  rather than recalculated ad hoc inside API queries

## Dependencies

- `R-028-03`
- `R-042-05`
- `R-044-01`

## Scope

### Introduce A Dedicated Album Person-Group Derive Job

Add one derive job responsible for building person-group relevance links from
canonical album data.

Recommended job identity:

- CLI name: `album-aggregate`

### Use Canonical Person Evidence From Assets

The derive job should treat a person as present in a folder or collection when
that person is evidenced by at least one contained asset through either:

- `AssetPerson.person_id`
- `Asset.creator_person_id`

For one asset, those two evidence sources should be unioned into one distinct
person set before group matching is calculated.

This prevents double-counting the same person when they appear both as asset
creator and as an associated asset person.

### Aggregate Relevance For Every Album Node

The derive output should materialize relevance for every folder node and every
collection node, not only for leaves.

Required direction:

- a parent folder inherits the union of qualifying evidence from all descendant
  folders and directly assigned assets
- a parent collection inherits the union of qualifying evidence from all
  descendant collections and direct collection members

This keeps the derive semantics aligned with the existing album-navigation
behavior where parent nodes are selectable aggregate nodes.

### Add Explicit Derived Association Tables

Add two derived-owned association tables:

- `asset_folder_person_group`
- `asset_collection_person_group`

Separate tables are preferred over one polymorphic `album_node_person_group`
table because folders and collections are already modeled as distinct
structures with distinct traversal and query behavior.

### Define The Folder Relevance Table

`asset_folder_person_group` should contain:

- `folder_id`
- `group_id`
- `matched_person_count`
- `group_person_count`
- `matched_asset_count`
- `matched_creator_person_count`

Constraints and indexes:

- primary key or unique constraint on `(folder_id, group_id)`
- index on `group_id`
- index on `matched_person_count`

Column semantics:

- `matched_person_count`
  - number of distinct members of the person group evidenced anywhere in the
    aggregated folder node
- `group_person_count`
  - total number of members currently in the referenced person group
- `matched_asset_count`
  - number of distinct assets in the aggregated folder node that contain at
    least one member of the person group
- `matched_creator_person_count`
  - number of distinct group members contributed through
    `Asset.creator_person_id`

The task should not persist a precomputed percentage column. Coverage ratios
should be derived from `matched_person_count / group_person_count` at read
time.

### Define The Collection Relevance Table

`asset_collection_person_group` should mirror the same contract for collection
selection:

- `collection_id`
- `group_id`
- `matched_person_count`
- `group_person_count`
- `matched_asset_count`
- `matched_creator_person_count`

Constraints and indexes:

- primary key or unique constraint on `(collection_id, group_id)`
- index on `group_id`
- index on `matched_person_count`

### Keep The Materialized Model Minimal And Queryable

The derive tables should store only stable query primitives needed for
relevance lookup and ranking.

Required direction:

- do not duplicate person ids into JSON blobs
- do not store per-asset explanation payloads in this increment
- do not add a generic metadata column unless a concrete read need appears

The canonical graph remains the explorable evidence layer. The derived tables
exist to make album-to-group and group-to-album discovery fast and explicit.

### Rebuild The Associations Deterministically

The derive job should recompute the full folder and collection relevance
materialization deterministically from canonical state.

The implementation should define one explicit reconciliation strategy, for
example:

- clear and rebuild both derived tables inside one derive run
- or replace per-node rows deterministically during one full scan

The chosen strategy must be idempotent and leave no duplicate or stale
associations after repeated runs.

### Expose Read Paths Through Repositories

The persistence layer should expose explicit repository methods for both lookup
directions:

- list person-group relevance rows for one folder
- list person-group relevance rows for one collection
- list relevant folders for one person group
- list relevant collections for one person group

Deterministic ordering should be defined. Recommended default ordering:

1. descending `matched_person_count`
2. descending `matched_asset_count`
3. stable node name or path

### Cover Edge Cases In Tests

Tests should explicitly cover:

- groups with zero members
- one person belonging to multiple groups
- assets that contribute only through `creator_person_id`
- assets that contribute through both `AssetPerson` and `creator_person_id`
- parent folder aggregation across descendants
- parent collection aggregation across descendants
- folders or collections with no qualifying group matches
- repeated derive execution without duplicate rows
- group membership changes reflected after rerun

## Out of Scope

- no UI changes yet
- no API route changes yet
- no generic album-node polymorphism layer
- no persistence of matched person id lists or explanation JSON
- no event-based person-group aggregation outside album structures

## Acceptance Criteria

- a dedicated derive job exists for materializing album person-group relevance
- the job is explicitly scoped to both folders and collections
- canonical person evidence is derived from `AssetPerson` plus
  `Asset.creator_person_id`
- explicit derived tables exist for folder-to-group and collection-to-group
  relevance
- each relevance row stores matched distinct-person counts and group-size
  counts rather than only a boolean flag
- parent folders and parent collections receive descendant-aware aggregated
  relevance
- repeated runs are deterministic and idempotent
- repository read paths exist for both album-to-group and group-to-album
  lookup

## Notes

The key design decision is to materialize group relevance, not to denormalize
all person evidence into album nodes.

That keeps the model aligned with PixelPast's layering:

- canonical tables hold assets, persons, and memberships
- derived tables hold query-oriented aggregate links

If later UI work needs richer explanation such as "which exact members caused
this group to rank highly here", that should be introduced as a focused follow
up after concrete read requirements exist.
