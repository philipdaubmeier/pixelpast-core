# R-022-01 - Photo Ingest Contracts and Characterization

## Goal

Create safe refactoring seams before moving logic out of
`ingestion/photos/service.py` and `ingestion/photos/connector.py`.

The current photo ingest code already works and is covered by useful tests, but
many important contracts are still implicit:

- public imports from `pixelpast.ingestion.photos`
- `PhotoConnector` override points used by tests
- progress event names and counter semantics
- `PhotoIngestionResult` field meanings

This task should make those contracts explicit and stable so later extraction
steps can stay behavior-preserving.

## Dependencies

- none

## Scope

### Extract Public Photo Ingest Contracts

Move the public photo-ingest data contracts into an explicit module such as
`ingestion/photos/contracts.py` or `ingestion/photos/models.py`.

At minimum, cover:

- `PhotoAssetCandidate`
- `PhotoPersonCandidate`
- `PhotoDiscoveryError`
- `PhotoDiscoveryResult`
- `PhotoMetadataBatchProgress`
- `PhotoIngestionResult`

`PhotoIngestionProgressSnapshot` may remain an alias to the generic ingestion
snapshot, but its public import path must stay stable.

### Preserve Existing Import Paths

The following imports must continue to work after this task:

- `from pixelpast.ingestion.photos import ...`
- imports from `pixelpast.ingestion.photos.connector`
- imports from `pixelpast.ingestion.photos.service`

Re-exports are acceptable and preferred over forcing downstream changes.

### Lock Down Behavioral Contracts

Add or tighten characterization coverage for the contracts that later tasks must
not accidentally change:

- `PhotoConnector.discover_paths(...)`
- `PhotoConnector.extract_metadata_by_path(...)`
- `PhotoConnector.build_asset_candidate(...)`
- `PhotoIngestionService.ingest(...)`
- progress event names:
  - `phase_started`
  - `phase_completed`
  - `metadata_batch_submitted`
  - `metadata_batch_completed`
  - `run_finished`
  - `run_failed`
- persistence outcome semantics:
  - `inserted`
  - `updated`
  - `unchanged`

If useful, split the current large photo-ingest test module into smaller
concern-oriented modules, but do not weaken assertions.

### Prepare the Package for Follow-Up Extraction

Create the internal package layout needed by later tasks only where it reduces
move noise and import churn.

Examples:

- `ingestion/photos/discovery.py`
- `ingestion/photos/fetch.py`
- `ingestion/photos/transform.py`
- `ingestion/photos/persist.py`
- `ingestion/photos/progress.py`

These files may initially contain thin wrappers or re-exports only.

## Out of Scope

- no behavior changes
- no new generic ingestion framework
- no progress redesign
- no connector logic extraction yet
- no service orchestration changes yet

## Acceptance Criteria

- the full existing photo-ingest test coverage still passes
- public imports from `pixelpast.ingestion.photos` remain stable
- existing `PhotoConnector` subclass-based tests continue to work
- progress event names and result field semantics are explicitly covered by
  tests or equivalent characterization coverage
- later refactoring tasks can move code without first having to discover hidden
  public contracts

## Notes

This task is intentionally conservative. The point is to freeze behavior before
improving structure.
