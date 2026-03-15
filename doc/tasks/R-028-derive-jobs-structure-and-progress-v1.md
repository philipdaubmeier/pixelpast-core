# R-028 - Derive Jobs Structure and Progress v1

## Goal

Refactor the derive-job implementation into a cleaner responsibility split that
mirrors the intent of the `R-022-xx` ingest-worker refactoring, while staying
proportionate to the current complexity of the derive layer.

Today the derive side is still small: `daily_aggregate.py` owns canonical input
loading, aggregation, persistence orchestration, and terminal result assembly in
one place, while the CLI derive path has no phase-aware live progress reporting
and no dedicated persisted run tracking analogous to ingest.

This task series should introduce:

- a thin derive-job orchestration shape
- explicit collaborators for the daily aggregate job where responsibilities are
  already distinct
- persisted derive-run lifecycle and progress visibility in the database
- CLI progress output for `pixelpast derive ...`
- reuse of the existing generic progress runtime shared with ingest

The implementation must not overreact to one job by introducing a broad derive
framework.

## Dependencies

- `R-023-02`
- `R-025`

## Scope

### Mirror the Ingest Refactoring at the Right Scale

Use the `R-022-xx` ingest refactoring as the design reference for
responsibility boundaries, not as a mandate to copy every abstraction.

The derive side should end up with the same architectural clarity:

- entrypoint / facade
- run lifecycle coordination
- progress reporting
- domain-specific read/build/persist collaborators

But it should not introduce a generic staged derive runner unless the current
code genuinely proves one is needed.

### Keep the Shared Progress Runtime Shared

The derive implementation must reuse the existing generic progress classes and
runtime mechanics already used by ingest.

Do not introduce a second generic progress engine.

If the current engine needs a small extension so derive runs can persist through
their own repository, keep that extension narrow and make sure ingest behavior
stays stable.

### Make Progress Visible in Both Persistence and CLI

The derive path should become operationally inspectable in the same way ingest
already is:

- current phase visible while the job is running
- periodic heartbeat / progress persistence in the database
- terminal summary with meaningful counters
- CLI-visible progress lines during `pixelpast derive ...`

### Break the Work Into Focused Subtasks

Implement this task series through the following subtasks:

- `R-028-01`
  - split daily aggregate derive responsibilities into explicit collaborators
- `R-028-02`
  - introduce derive-run lifecycle persistence and shared-progress integration
- `R-028-03`
  - surface derive progress in the CLI using the shared progress contract

## Out of Scope

- no generic multi-job derive framework
- no background worker or scheduling redesign
- no UI screen for live derive monitoring
- no change to daily aggregate product semantics beyond what is needed to expose
  structured progress and cleaner orchestration

## Acceptance Criteria

- the daily aggregate derive path no longer keeps all orchestration, read,
  aggregation, persistence, and progress responsibilities in one file-level
  implementation bucket
- derive runs have persisted lifecycle and progress visibility analogous to
  ingest, without overloading ingest-specific database concepts
- `pixelpast derive daily-aggregate` emits meaningful phase-aware CLI progress
- the derive implementation reuses the existing generic progress runtime instead
  of introducing a parallel progress stack
- the resulting structure is intentionally small and justified by the current
  derive-layer complexity

## Notes

The design target is a derive path that is easier to reason about, test, and
extend to one or two additional jobs later, not a reusable workflow engine.
