# R-021 - Photo Ingest Observability and Progress v1

## Goal

Improve the operational transparency and debuggability of photo ingestion runs.

The current photo ingest path can appear stuck from the CLI when scanning a real
directory, especially during metadata extraction and persistence phases. This
task should make ingestion visibly alive, measurable, and diagnosable both from
the command line and from persistence state.

The result should be an ingest workflow where a user can answer, at any point
in time:

- is the job still alive?
- which phase is it currently executing?
- how many files were discovered?
- how many files have already been analyzed?
- how many files have been persisted?
- how many records were inserted, updated, left unchanged, or skipped?
- how many previously known source items are no longer present in the source
  directory?

---

## Scope

Implement a first operational-observability increment for the photo ingestion
connector and CLI.

### Runtime Progress Visibility

The ingest must expose meaningful progress while it is running.

At minimum, progress visibility must cover these phases:

- filesystem discovery
- metadata extraction
- canonical persistence
- finalization

The implementation must make it visible:

- when a phase starts
- when a phase finishes
- how many items are in scope for that phase
- how many items have already completed within that phase

The implementation should avoid long periods of apparent silence.

### CLI Progress Output

The `pixelpast ingest photos` command should display user-visible progress while
running.

The CLI output must:

- show that the process is alive while long-running work is in progress
- expose current phase information
- show progress counts in a way that is understandable to a terminal user
- work with ordinary local terminals on Windows

Using a standard CLI progress bar or spinner library is acceptable if it fits
the project style, but raw structured progress lines are also acceptable if
they are clearer and more robust.

At minimum, the CLI should surface:

- discovered file count
- metadata batches submitted to `exiftool`
- metadata batches completed
- assets persisted so far
- inserted asset count
- updated asset count
- unchanged asset count
- skipped / errored file count

The CLI should also make batch progress visible during metadata extraction so
that `exiftool` activity is not a black box.

### Periodic Database Progress Updates

The current `ImportRun` tracking is too coarse for long-running operational
jobs.

Extend ingestion-state persistence so that the current job state is updated
regularly while the run is still in progress.

At minimum, the persisted state must be refreshed at least every 10 seconds
while work is ongoing.

The persisted runtime state should include enough information to answer:

- whether the job is still alive
- what phase it is currently in
- when the last heartbeat / progress update was written
- how far the job has progressed numerically

This task should review whether these attributes belong directly on
`ImportRun`, in a dedicated progress JSON field, or in another minimal schema
extension. The chosen design must be explicit and justified by maintainability
and queryability.

### Counters and Result Semantics

The ingestion result model should become more operationally meaningful.

At minimum, the implementation must distinguish:

- discovered files
- files successfully analyzed
- files failed during analysis
- assets inserted
- assets updated because canonical values changed
- assets already up to date and therefore unchanged
- assets skipped for other reasons, if applicable

The implementation must define these terms deterministically.

In particular, `updated` and `unchanged` must not be ambiguous:

- `updated` means an already-known canonical asset existed and at least one
  persisted canonical field or association changed during this run
- `unchanged` means an already-known canonical asset existed and the ingest
  determined that the canonical persisted state already matched the newly
  extracted canonical state

### Removed-From-Source Visibility

The product still does not support delete synchronization in this phase, and
that remains out of scope.

However, the ingest should surface the count of previously known photo assets
for the source that are no longer present under the configured root directory.

This task must define and expose a non-destructive metric such as:

- `missing_from_source_count`

This metric is informational only in this phase:

- do not delete canonical records
- do not mark assets inactive unless a separate schema decision is explicitly
  introduced

The goal is operational visibility, not delete reconciliation.

### Logging and Diagnostics

The ingest should emit structured progress logs in addition to CLI-facing
progress display.

Logs should make it possible to diagnose where a job spent time, including:

- discovery start and finish
- number of supported files found
- metadata extraction batch sizes
- metadata extraction batch completion
- persistence progress checkpoints
- heartbeat writes
- terminal status and summary

If the ingest fails, the logs should make the last known phase and counters
easy to understand.

### Hang Detection and Liveness Hardening

This task should improve the ability to detect and diagnose hangs or stalls.

The implementation must make a stalled job observable through persisted state.

At minimum:

- a running job must update a heartbeat / progress timestamp regularly
- the currently active phase must be persisted
- if a sub-step is batch-oriented, the current batch position should be visible

This task does not require a full watchdog or job-cancellation system, but it
should leave the system in a materially more diagnosable state when a run
stalls.

### Independent Testability

The observability behavior must remain testable independently from the UI.

Tests should cover:

- CLI execution against a real fixture directory
- progress state persistence during an ingest run
- correct terminal summary counters
- heartbeat updates during a long-running ingest simulation
- clear failure behavior when progress cannot continue

At least one CLI integration test should run `pixelpast ingest photos` against:

- a temporary SQLite database
- the prepared fixture directory `test/assets`

That test should verify both:

- successful completion
- meaningful persistence and/or output progress behavior

---

## Out of Scope

- no UI screen for live ingest monitoring
- no remote job queue or background worker framework
- no cancellation API
- no delete synchronization that mutates canonical assets
- no performance optimization beyond what is necessary to expose progress
- no general-purpose observability platform integration
- no metrics backend such as Prometheus

---

## Acceptance Criteria

- running `pixelpast ingest photos` against a real photo directory produces
  visible progress during execution instead of appearing silent
- the CLI exposes phase-aware progress for discovery, metadata extraction, and
  persistence
- metadata extraction progress is visible at batch granularity
- the ingest persists periodic in-progress updates at least every 10 seconds
- the persisted in-progress state includes:
  - current phase
  - last heartbeat / progress update timestamp
  - numeric progress counters sufficient to understand job advancement
- terminal run summaries clearly distinguish:
  - discovered
  - analyzed
  - analysis_failed
  - inserted
  - updated
  - unchanged
  - skipped
  - missing_from_source
- `updated` versus `unchanged` semantics are deterministic and covered by tests
- the ingest exposes an informational count of previously known source assets
  that are no longer present in the configured photo root
- a stalled job can be diagnosed from persistence and logs without relying on
  guesswork
- the repository contains automated tests that exercise the full CLI path
  against `test/assets` and a temporary SQLite database
- the repository contains tests for periodic progress persistence / heartbeat
  behavior

---

## Notes

This task is motivated by real operational ambiguity observed during
`pixelpast ingest photos` runs against local directories.

The key objective is not only better logging, but end-to-end operational
visibility:

- terminal users should see forward progress
- persistence should reflect forward progress
- a later UI or operational tool should be able to inspect the current job
  state without parsing terminal output

Because `ImportRun` already exists as the canonical job-tracking concept, this
task should prefer extending or cleanly complementing that model instead of
introducing an unrelated parallel tracking mechanism.

Be explicit about whether counters are file-based, asset-based, or
association-based, and keep those semantics consistent across CLI output,
logging, and persistence.
