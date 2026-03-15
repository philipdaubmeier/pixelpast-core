# R-029 - CLI Progress Bar Reporting

## Goal

Replace the current line-oriented CLI progress output for shared job progress
with a conventional terminal progress bar presentation.

Today progress snapshots are rendered as repeated textual status lines in the
CLI. That is functional, but noisy and visually weaker than the standard
progress-bar experience users expect from long-running terminal jobs.

This task should introduce a common CLI progress-bar renderer for shared job
progress so ingest and derive runs show:

- the current phase
- item `x` of `total`
- percentage progress
- a visible progress bar

The result should feel like a standard operational CLI, not a log stream.

Only at the end of an ingest or derive job after the last phase was finished
show a summary of inserted, updated, skipped etc. number of files, like
currently already implemented. Maybe improve the formatting and print it out
in separate lines and visually more pleasing.

## Dependencies

- `R-028-03`

## Scope

### Replace Repeated Progress Lines with a Real Progress Bar

The current CLI reporting path should stop printing a new text line for every
progress update during normal execution.

Instead, progress updates should refresh a single terminal progress display in
place, using a widely used library that works reliably in ordinary local
terminals on Windows.

Acceptable options include a mainstream library such as:

- `tqdm`
- `rich`

Choose one implementation path and use it consistently rather than introducing
an abstraction over multiple progress-bar backends.

### Keep the Shared Progress Contract Stable

This task is about CLI rendering, not about redefining the shared progress
runtime.

`src/pixelpast/shared/progress.py` should remain the source of truth for the
phase-aware snapshot contract and persistence behavior unless a very small,
rendering-driven adaptation is genuinely necessary.

Do not move CLI-specific terminal behavior into the shared runtime if it would
blur the separation between:

- shared progress state and callbacks
- CLI presentation

If the current implementation routes progress-to-CLI behavior outside
`src/pixelpast/shared/progress.py`, keep that boundary explicit.

### Render Only the Core Operational Signals

The progress bar presentation should stay intentionally minimal.

During active execution, the visible CLI state should focus on:

- current phase label
- completed item count
- total item count when known
- percentage
- progress bar visualization

Do not keep rendering the full detailed counter set on every in-flight update
if that would clutter the terminal.

### Preserve Clear Terminal Summaries

The final terminal summary after job completion or failure should remain
explicit textual output.

A progress bar is appropriate for in-flight rendering, but terminal completion
should still produce a deterministic summary line or short summary block that
captures the final result.

### Handle Unknown Totals Gracefully

Some phases may not know `total` up front.

The chosen CLI progress-bar approach must define clear behavior for
`total=None`, for example by:

- showing an indeterminate-style progress indicator
- delaying bar creation until a total becomes known
- falling back to a minimal non-noisy status presentation for that phase

The behavior must be explicit and consistent across ingest and derive.

### Keep Ingest and Derive on One CLI Vocabulary

Ingest and derive should continue to share one progress presentation model.

Do not introduce a separate derive-only or ingest-only bar style unless there
is a concrete user-facing requirement that justifies divergence.

### Add CLI-Focused Tests

Update CLI tests so they verify the new rendering behavior at the level that is
stable and meaningful for automated tests.

Tests should cover:

- phase-aware progress bar initialization
- progress advancement within a phase
- terminal summary output after successful completion
- terminal summary output after failure
- compatibility with both ingest and derive command paths

Avoid brittle assertions against overly specific terminal-control sequences if
the chosen library makes that unstable.

## Out of Scope

- no changes to ingestion or derive business logic
- no TUI dashboard beyond a single conventional progress-bar presentation
- no remote progress monitoring
- no redesign of persisted progress payload semantics

## Acceptance Criteria

- running long-lived CLI jobs no longer emits repeated progress log-style lines
  for every update during normal progress reporting
- the CLI shows a conventional progress bar with phase, completed count, total
  count when available, and percentage
- the chosen progress-bar library works in ordinary local Windows terminals
- ingest and derive share the same CLI progress rendering approach
- final completion and failure states still produce deterministic textual
  summaries
- automated tests cover the new CLI reporting behavior without relying on
  fragile terminal-control details

## Notes

The design objective is operational clarity with lower terminal noise.

This task should prefer a proven library over a custom in-place redraw
implementation, provided the library integrates cleanly with Typer-based CLI
execution and does not weaken testability.
