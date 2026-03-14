# R-022-03 - Photo Ingest Metadata Transform Extraction

## Goal

Isolate the pure metadata-to-canonical transformation logic from
`ingestion/photos/connector.py`.

Today the connector contains a large cluster of functions that determine how raw
metadata becomes a `PhotoAssetCandidate`. That is the real photo-specific domain
logic and should be easy to read, test, and evolve independently from traversal
or subprocess concerns.

## Dependencies

- `R-022-01`
- `R-022-02`

## Scope

### Introduce a Dedicated Photo Transform Component

Create a focused component such as:

- `PhotoAssetCandidateBuilder`
- `PhotoMetadataTransformer`

It should accept the inputs that define one transform operation:

- the resolved file path
- fetched metadata for that file
- fallback EXIF metadata

and produce:

- one `PhotoAssetCandidate`

### Move Canonical Mapping Logic Out of `PhotoConnector`

Relocate the transformation helpers into the new module/component:

- `extract_photo_exif_metadata(...)`
- `_resolve_first_string(...)`
- `_resolve_photo_timestamp(...)`
- `_resolve_photo_coordinates(...)`
- `_extract_explicit_tag_labels(...)`
- `_extract_hierarchical_paths(...)`
- `_expand_hierarchy_paths(...)`
- `_resolve_person_candidates(...)`
- `_extract_face_region_names(...)`
- `_resolve_matching_person_path(...)`
- `_resolve_asset_tag_paths(...)`
- `_resolve_explicit_tag_path(...)`
- `_build_metadata_json(...)`
- `_normalize_hierarchy_path(...)`
- `_coerce_string_list(...)`
- `_resolve_first_string_list(...)`
- `_coerce_float(...)`
- `_parse_filename_timestamp(...)`
- `_parse_exif_datetime(...)`
- `_extract_gps_coordinates(...)`
- `_parse_gps_coordinate(...)`

### Keep `PhotoConnector.build_asset_candidate(...)` Stable

`PhotoConnector.build_asset_candidate(...)` must keep the same public signature
and return value. In this task it becomes a thin facade over the dedicated
transform component.

### Preserve Deterministic Resolution Semantics

The extraction must preserve all current precedence and fallback behavior:

- title resolution order
- creator resolution order
- timestamp precedence and fallback chain
- GPS precedence and fallback chain
- tag hierarchy materialization
- face-region person handling
- metadata JSON shape and resolution metadata

### Favor Pure, Small Units

The new transform code should be organized around pure functions or a narrowly
scoped builder class. Avoid coupling it to traversal, subprocess handling, or
database repositories.

## Out of Scope

- no filesystem traversal extraction yet
- no service orchestration changes yet
- no repository or persistence refactor yet
- no generic ingest abstraction yet

## Acceptance Criteria

- current precedence and fallback tests still pass unchanged
- fixture-based metadata enrichment tests still pass unchanged
- `PhotoConnector.build_asset_candidate(...)` remains stable for existing callers
- the metadata transformation logic can be read and tested independently from
  the connector facade

## Notes

This task is the core domain extraction step. It should leave the photo-specific
mapping logic obvious enough that future connector work does not require reading
through subprocess and traversal code first.
