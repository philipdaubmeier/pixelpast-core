# R-022-04 - Photo Connector Facade and Discovery Split

## Goal

Shrink `ingestion/photos/connector.py` into a thin facade and align the photo
connector with the architecture-level stages:

- discover
- fetch
- transform

After `R-022-02` and `R-022-03`, the remaining connector-specific concern is
filesystem discovery. This task extracts that concern and makes the connector a
clear composition root instead of a thousand-line implementation bucket.

## Dependencies

- `R-022-02`
- `R-022-03`

## Scope

### Introduce a Dedicated File Discovery Component

Create a component such as `PhotoFileDiscoverer` that owns:

- root validation
- recursive traversal
- supported-extension filtering
- stable path ordering
- per-path progress callback invocation

### Turn `PhotoConnector` Into a Thin Composition Facade

`PhotoConnector` should compose:

- the file discoverer
- the metadata fetcher
- the asset candidate builder

Its public methods remain:

- `discover_paths(...)`
- `extract_metadata_by_path(...)`
- `build_asset_candidate(...)`
- `discover(...)`

### Clarify the Role of `discover(...)`

The current `discover(...)` convenience method is not used by the ingest
service, but it is still a public connector method.

In this task, make its role explicit:

- keep it as a convenience wrapper that combines discover, fetch, and transform
- ensure it delegates to the newly extracted components
- keep `PhotoDiscoveryResult` unchanged

### Preserve Existing Extension and Test Seams

Existing tests subclass `PhotoConnector` and override methods directly. This
task must not casually break that capability.

Acceptable strategies:

- keep the current overridable methods and have them delegate internally
- preserve subclass override behavior through explicit template methods
- adapt tests only minimally if a clearer seam is introduced

### Document Component Responsibilities

The resulting structure should make it visually obvious which code belongs to:

- file discovery
- raw metadata fetching
- metadata transformation

## Out of Scope

- no persistence refactor yet
- no progress-tracker refactor yet
- no generic base service yet
- no UI or CLI behavior changes

## Acceptance Criteria

- file discovery behavior remains unchanged
- `PhotoConnector` public methods and return types remain stable
- existing subclass-based test doubles still work or require only minimal,
  behavior-preserving adaptation
- `connector.py` becomes a small facade or compatibility layer rather than the
  home of all real logic

## Notes

At the end of this task, the photo connector should already look like a
connector again instead of a monolith.
