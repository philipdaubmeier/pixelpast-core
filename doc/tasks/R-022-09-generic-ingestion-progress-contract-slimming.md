# R-022-09 - Generic Ingestion Progress Contract Slimming

## Goal

Reduce the generic ingestion progress contract to the minimum set of fields that
is broadly useful across all current and planned ingestion workers.

The current generic progress model in `ingestion/progress.py` is nominally
source-agnostic, but in practice it still carries several photo-specific or
batch-tool-specific fields. This makes the abstraction heavier than necessary
and risks forcing unrelated future connectors into a progress vocabulary that
does not fit them well.

This task should redefine the generic progress contract around:

- phase-local runtime progress
- cumulative run outcomes

and remove source-specific transport details from the generic layer.

## Dependencies

- `R-022-07`
- `R-022-08`

## Scope

### Slim the Generic Snapshot Shape

Refactor the generic `IngestionProgressSnapshot` so it only contains fields that
are broadly meaningful for all ingestion workers.

The target generic contract should be centered on:

- `source`
- `import_run_id`
- `phase`
- `status`
- `total`
- `completed`
- `inserted`
- `updated`
- `unchanged`
- `skipped`
- `failed`
- `missing_from_source`

Exact naming may vary slightly, but the semantics must match this model.

### Define Field Semantics Explicitly

The reduced snapshot contract must define these meanings explicitly:

- `total`
  - the total number of units in the current phase when known
  - `None` when the phase is open-ended or not knowable in advance
- `completed`
  - the number of units completed within the current phase
- `inserted`
  - cumulative count of newly inserted canonical records for the run
- `updated`
  - cumulative count of previously known canonical records that changed
- `unchanged`
  - cumulative count of previously known canonical records that required no
    canonical update
- `skipped`
  - cumulative count of intentionally skipped units that are not counted as
    failures
- `failed`
  - cumulative count of non-fatal unit-level failures within the run
- `missing_from_source`
  - informational count of previously known source items not present in the
    current source scan

### Remove Redundant Fields From the Generic Layer

Remove the following fields from the generic progress snapshot and persisted
generic progress state:

- `phase_status`
- `discovered_file_count`
- `analyzed_file_count`
- `analysis_failed_file_count`
- `metadata_batches_submitted`
- `metadata_batches_completed`
- `items_persisted`
- `current_batch_index`
- `current_batch_total`
- `current_batch_size`

These either duplicate other information, encode photo-specific workflow
details, or describe transport-level batch mechanics that do not belong in the
generic contract.

### Keep Phase Progress Explicit

The generic progress contract must treat `total` and `completed` as phase-local
progress values, not as global run totals.

Examples:

- during filesystem discovery, `total/completed` describe discovery progress
- during metadata analysis, `total/completed` describe analysis progress
- during persistence, `total/completed` describe persistence progress

This phase-local interpretation should replace the need for dedicated counters
such as `discovered_file_count` or `analyzed_file_count`.

### Move Batch Diagnostics Out of Generic Progress

Batch-oriented details such as exiftool submission and completion counts should
no longer be modeled as part of the generic ingestion progress contract.

These details should instead live in one of the following, as appropriate:

- structured logs
- source-specific internal diagnostics
- optional source-specific debug events if truly needed later

This task should not preserve batch transport details in the generic snapshot
just for historical compatibility if they are not broadly useful.

### Update the Generic Progress Engine

Refactor `IngestionProgressEngine` and its state model to support the slimmed
contract.

The engine should remain responsible for:

- phase transitions
- terminal status persistence
- heartbeat persistence cadence
- callback emission

But it should no longer assume photo-specific counters.

### Adapt the Photo Progress Adapter

Update the photo-specific progress adapter to map its local behavior onto the
new generic contract.

For the photo ingest path:

- `failed` should replace `analysis_failed_file_count` in the generic snapshot
- `total/completed` should represent the active phase progress
- source-specific batch tracking should no longer inflate the generic snapshot

If the photo connector still wants to log metadata batch transitions, that is
acceptable, but those details should stay outside the generic progress contract.

### Review CLI and Persistence Consumers

Update all consumers of `IngestionProgressSnapshot` and persisted progress JSON
to use the new semantics.

At minimum, review:

- ingest CLI progress rendering
- photo progress callbacks in tests
- import-run progress persistence payload shape

The CLI should continue to show meaningful progress, but it should derive that
from the slimmed contract rather than from photo-specific fields that no longer
belong in the generic model.

## Out of Scope

- no new UI for live ingest monitoring
- no reintroduction of source-specific debug payloads into the generic snapshot
- no broader ingestion architecture changes outside progress/state consumers
- no change to source-specific business semantics such as what counts as
  `updated`, `unchanged`, or `missing_from_source`

## Acceptance Criteria

- the generic progress snapshot contains only broadly reusable progress and
  outcome fields
- `phase_status` is removed and `phase + status` are sufficient to interpret the
  run state
- phase-local progress is expressed only through `total` and `completed`
- cumulative run outcomes are expressed only through:
  - `inserted`
  - `updated`
  - `unchanged`
  - `skipped`
  - `failed`
  - `missing_from_source`
- transport-level batch details are no longer part of the generic progress
  contract
- photo ingest continues to provide meaningful progress reporting using the
  slimmer contract
- existing tests are updated as needed to assert the new contract precisely
- the resulting generic progress layer is smaller, clearer, and no longer
  coupled to photo-specific analysis terminology

## Notes

This task intentionally distinguishes between:

- generic progress state that every ingest worker can understand
- source-specific operational diagnostics that may still be useful in logs

That separation is the main design objective.
