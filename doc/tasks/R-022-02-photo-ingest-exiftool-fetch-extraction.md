# R-022-02 - Photo Ingest Exiftool Fetch Extraction

## Goal

Remove exiftool process handling, batch planning, timeout splitting, and raw
metadata indexing from `ingestion/photos/connector.py`.

The connector currently mixes:

- filesystem traversal
- exiftool execution
- timeout recovery
- metadata indexing
- canonical transformation

This task isolates the `fetch()` part of the ingest pipeline behind a dedicated
component while preserving the existing `PhotoConnector` API.

## Dependencies

- `R-022-01`

## Scope

### Introduce a Dedicated Metadata Fetch Layer

Create a photo metadata fetch component, for example:

- `PhotoMetadataFetcher`
- `ExiftoolJsonBatchRunner`

The exact naming is flexible, but responsibilities must be explicit.

### Move Raw Fetch Logic Out of `PhotoConnector`

Relocate the following logic into the new fetch layer:

- `_chunked(...)`
- `_metadata_batches_for_paths(...)`
- `_count_batches(...)`
- `_index_metadata_results(...)`
- `_run_exiftool_json(...)`
- recursive timeout split handling from
  `_extract_batch_metadata_with_fallback(...)`

### Keep `PhotoConnector.extract_metadata_by_path(...)` Stable

`PhotoConnector.extract_metadata_by_path(...)` must remain available with the
same signature and callback behavior. In this task it becomes a thin facade that
delegates to the dedicated fetch layer.

### Preserve Existing Error and Progress Semantics

The new fetch layer must preserve the current behavior exactly:

- missing `exiftool` still surfaces the same runtime failure semantics
- invalid or empty exiftool output still fails deterministically
- timeout handling still splits batches recursively until single files
- single-file timeout fallback still returns a minimal `{"SourceFile": ...}`
  payload
- metadata batch callbacks still emit the same batch index, total, and size

### Keep Batch Policy Explicit

Batch size, timeout, and metadata command parameters should remain explicit and
local to the fetch layer rather than scattered across the connector facade.

## Out of Scope

- no canonical field mapping changes
- no tag or person resolution changes
- no filesystem discovery extraction yet
- no persistence refactor yet
- no generic base connector yet

## Acceptance Criteria

- current exiftool-related tests still pass without semantic changes
- `PhotoConnector.extract_metadata_by_path(...)` still works for existing test
  doubles and callers
- `connector.py` no longer owns subprocess execution details
- the new fetch component is independently testable without exercising the full
  ingest service

## Notes

This task should leave a clear seam for future video or media connectors that
also need external metadata tooling without copying subprocess boilerplate.
