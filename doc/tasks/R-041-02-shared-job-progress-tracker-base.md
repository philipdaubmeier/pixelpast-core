# R-041-02 - Shared Job Progress Tracker Base

## Goal

Extract the repeated tracker shell around `JobProgressEngine` into one reusable
base shared by ingestion and derive jobs.

The current connector progress modules repeatedly implement the same mechanics:

- engine construction
- phase start and completion handling
- snapshot emission
- heartbeat logging
- terminal success and failure handling

This task should reduce that duplication while preserving all current progress
semantics, callback behavior, and persisted payload fields.

## Dependencies

- none

## Scope

### Introduce a Shared Tracker Base over the Existing Engine

Create a reusable tracker base or equivalent helper above
`pixelpast.shared.progress.JobProgressEngine`.

It should own the repeated mechanics for:

- constructing the engine
- emitting snapshots
- logging heartbeat writes
- finishing or failing a run
- rendering the generic snapshot shape

The implementation should be usable by both:

- ingestion progress adapters
- derive progress adapters

If placement is ambiguous, prefer a shared module rather than an
ingestion-specific location.

### Keep Counter State Explicit and Job-Specific

Do not force all jobs into one giant counter dataclass.

Connector- and job-specific state should remain explicit and local where that
improves readability, for example:

- photo batch counters
- calendar persisted-event counters
- Google Places remote fetch counters

If small mixins or helper dataclasses are useful for the common fields, they are
acceptable, but the design should not hide job semantics behind clever generic
state machinery.

### Preserve Existing Progress Contracts

This task must not change:

- event names
- phase names
- persisted JSON field names
- callback snapshot shape
- heartbeat timing behavior
- connector-specific warning and error logging semantics

The refactor should be internal only.

## Out of Scope

- no new progress fields
- no progress-schema cleanup
- no CLI rendering changes
- no job-run persistence changes

## Acceptance Criteria

- ingestion and derive progress trackers share one common shell above
  `JobProgressEngine`
- connector- and job-specific counters remain explicit where needed
- all current progress payloads and snapshot contracts remain stable
- the shared abstraction reduces repeated `_emit`, heartbeat, snapshot, and
  terminal-run boilerplate

## Notes

The goal is narrow reuse. Keep the base focused on mechanics, not on
normalizing every counter vocabulary into one abstraction.
