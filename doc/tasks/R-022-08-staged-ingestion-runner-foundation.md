# R-022-08 - Staged Ingestion Runner Foundation

## Goal

Introduce a small reusable staged ingestion runner so future file-based
connectors such as video ingest do not have to copy the photo service control
flow.

This is the final refactoring step, not the first one. It should only be done
after the photo-specific responsibilities are already split into clean
collaborators.

## Dependencies

- `R-022-04`
- `R-022-05`
- `R-022-06`
- `R-022-07`

## Scope

### Introduce a Reusable Orchestration Shell

Create a generic runner or base service that owns the high-level control flow:

- discover units
- fetch metadata or raw payloads
- transform one source unit into one canonical candidate
- persist canonical candidates
- handle partial transform failures
- handle fatal persistence failures
- drive progress updates and terminal run state

### Keep the Abstraction Minimal

The abstraction should be the smallest reusable shell that the existing photo
ingest genuinely proves.

Acceptable forms:

- a template-method base class
- a composition-based runner with injected strategy objects
- a small orchestration helper built around protocols

Avoid building a framework.

### Adapt `PhotoIngestionService` to the Runner

`PhotoIngestionService` should become a thin composition root that wires:

- photo file discovery
- photo metadata fetching
- photo metadata transformation
- photo asset persistence
- import-run lifecycle handling
- progress engine

Its public API must remain stable:

- `PhotoIngestionService(...)`
- `PhotoIngestionService.ingest(...)`
- `PhotoIngestionResult`

### Preserve Existing Entry Points

`run_ingest_source(...)` and the CLI ingest path must continue to behave as they
do today from the outside.

### Align With the Architecture Document

The final staged runner should make the architecture-level responsibilities
obvious:

- discover
- fetch
- transform
- persist

The photo implementation becomes the first concrete connector using that shape.

## Out of Scope

- no video ingest implementation yet
- no change to API or UI contracts
- no worker or scheduling redesign

## Acceptance Criteria

- all existing photo-ingest tests still pass
- `PhotoIngestionService` becomes a thin orchestration adapter rather than the
  home of all ingest behavior
- a future video-style file ingest can reuse the staged runner without copying
  photo-specific progress and transaction boilerplate
- the resulting abstraction is small, readable, and justified by the extracted
  responsibilities from the photo ingest path

## Notes

Prefer composition over inheritance if it keeps the control flow clearer. The
goal is reusable orchestration, not a deep connector class hierarchy.
