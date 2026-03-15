# R-028-03 - Derive CLI Progress Reporting

## Goal

Expose derive-job progress in the CLI in the same operational style as ingest,
using the shared progress contract established in `R-028-02`.

Today `pixelpast derive daily-aggregate` completes silently apart from log
output and final database effects. That makes long-running derive jobs feel
opaque compared with `pixelpast ingest photos`.

This task should make derive execution visibly alive from the terminal without
introducing a second CLI progress vocabulary.

## Dependencies

- `R-028-02`

## Scope

### Reuse or Narrowly Generalize the Existing CLI Reporter

Prefer reusing the current phase-aware CLI reporter used by ingest.

If the current `IngestionCliProgressReporter` name or placement is too
ingest-specific, generalize it narrowly so both ingest and derive can use the
same rendering behavior.

Do not create a second largely duplicated derive progress reporter unless there
is a clear, concrete formatting difference that the shared reporter cannot
handle cleanly.

### Show Phase-Aware Derive Progress

`pixelpast derive daily-aggregate` should emit meaningful terminal lines for:

- phase start
- in-phase progress updates
- phase completion
- terminal summary

The output should follow the shared progress semantics so users can read ingest
and derive progress the same way.

### Keep Summary Counters Meaningful for Derive

The terminal summary should show the shared counters, but only with semantics
that are justified by the current derive job.

For the daily aggregate job, define and expose the counters that are real and
deterministic for the current implementation. Counters that are structurally
unused may remain zero rather than forcing fake derive-specific arithmetic.

### Add CLI-Focused Tests

Expand CLI tests so the derive path verifies:

- visible phase output
- meaningful terminal summary output
- compatibility with full rebuild mode
- compatibility with range mode where relevant

The tests should assert human-meaningful progress behavior, not only exit codes.

## Out of Scope

- no TUI progress bars or spinner library
- no UI monitoring surface
- no changes to derive business logic beyond what is needed to report progress

## Acceptance Criteria

- running `pixelpast derive daily-aggregate` prints phase-aware progress lines
- derive CLI output uses the shared progress vocabulary rather than a second
  custom reporting format
- terminal summaries for derive jobs are deterministic and covered by tests
- ingest CLI progress behavior remains stable if the shared reporter is
  generalized

## Notes

The objective is operational consistency: ingest and derive should look like two
users of the same run-progress language, not two unrelated command styles.
