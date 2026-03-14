# R-022-07 - Ingestion Progress Engine Extraction

## Goal

Extract the heartbeat, phase-transition, snapshot-emission, and counter
bookkeeping mechanics from `ingestion/photos/service.py` into a reusable
ingestion progress engine.

The current `_PhotoIngestionProgressTracker` mixes two different concerns:

- generic mechanics:
  - phase transitions
  - heartbeat cadence
  - persistence of progress snapshots
  - callback emission
- photo-specific counter vocabulary

This task should separate those concerns without changing observable behavior.

## Dependencies

- `R-022-06`

## Scope

### Introduce a Generic Progress Runtime Component

Create a reusable progress module that owns the cross-cutting mechanics:

- entering or completing phases
- deciding when a heartbeat is due
- persisting progress snapshots
- emitting callbacks
- writing terminal success or failure state

### Model Counters Explicitly

Replace the current hand-mutated private counter object with an explicit
dataclass-based state model.

That model should provide small helper methods for deterministic state changes.
If arithmetic helpers such as `__add__` are genuinely useful, they may be
added, but only if they simplify real call sites.

### Preserve the Existing Snapshot Contract

For the photo ingest path, this task must preserve:

- `IngestionProgressSnapshot` shape
- event names
- phase names
- heartbeat timing behavior
- persisted progress JSON field names
- CLI-visible progress semantics

If needed, keep a photo-specific adapter or mapper around the generic engine so
the runtime mechanics can be shared without forcing premature schema changes.

### Keep Photo Aliases Stable

`PhotoIngestionProgressSnapshot` must remain importable from
`pixelpast.ingestion.photos`.

## Out of Scope

- no new UI for live monitoring
- no change to the CLI output contract
- no generalized staged ingest runner yet

## Acceptance Criteria

- heartbeat-related tests still pass unchanged
- CLI progress behavior for `pixelpast ingest photos` remains unchanged
- progress persistence still writes the same operationally meaningful fields
- `service.py` no longer owns a photo-specific implementation of generic
  heartbeat and phase-tracking mechanics

## Notes

Generalize the mechanics, not the whole world. If the counter vocabulary still
needs a photo-specific mapping layer after this task, that is acceptable.
