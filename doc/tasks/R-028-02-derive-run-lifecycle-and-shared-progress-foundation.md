# R-028-02 - Derive Run Lifecycle and Shared Progress Foundation

## Goal

Introduce persisted derive-run lifecycle tracking and phase-aware progress
reporting for derive jobs, using the existing shared progress runtime already
used by ingest.

The current derive path has no database-visible in-progress state analogous to
ingest. A long-running derive job therefore cannot answer basic operational
questions such as:

- is the job still alive?
- which phase is it in?
- how far has it progressed?
- what was the final terminal summary?

This task should add that visibility without overloading the ingest-specific
`ImportRun` concept and without creating a second generic progress stack.

## Dependencies

- `R-028-01`

## Scope

### Introduce a Dedicated Derive-Run Persistence Model

Add a minimal derive-run tracking concept for derived-data jobs.

It should be analogous to `ImportRun`, but derive-specific rather than a
semantic reuse of ingestion tables.

At minimum, the persisted derive-run record should support:

- job identity
- started and finished timestamps
- status
- current phase
- last heartbeat timestamp
- progress JSON payload
- enough run-mode context to distinguish full rebuilds from bounded runs

Keep the schema as small as the current derive CLI actually needs.

### Add a Derive Lifecycle Coordinator

Create a derive-run lifecycle collaborator that owns:

- derive-run creation
- initial zeroed progress payload creation
- terminal status persistence
- any minimal mode / parameter persistence for the current derive job

The daily aggregate job should not continue to hand-assemble operational run
state inline.

### Reuse the Existing Shared Progress Runtime

The implementation must reuse the existing generic progress classes and engine
that currently live in the ingest path.

If the engine is still too tied to `ImportRunRepository`, generalize it only
enough to persist progress through either:

- the existing import-run repository path
- a new derive-run repository path

Do not create:

- a second progress engine
- a derive-only snapshot type that duplicates the generic contract
- a second heartbeat implementation

If a tiny derive-specific wrapper or subclass is genuinely useful, it must be a
thin adaptation layer over the shared runtime rather than a parallel model.

### Define Derive Progress Semantics Explicitly

Apply the shared generic progress contract to derive jobs in a way that fits the
current daily aggregate complexity.

For the initial daily aggregate job, explicitly define:

- which phases are reported
- when `total` is known versus `None`
- what `completed` means in each phase
- how `inserted`, `updated`, `unchanged`, `skipped`, and `failed` map to derive
  outcomes

Do not invent derive-specific counters if the shared contract is already
sufficient.

If a count would require an expensive extra pass that is not justified today,
prefer `total=None` over adding new bookkeeping machinery.

### Make the Daily Aggregate Job Report Through the Shared Contract

Wire the daily aggregate job through the derive lifecycle and shared progress
runtime so progress is persisted during:

- canonical input loading
- aggregate construction
- aggregate persistence
- finalization

The implementation should emit phase transitions and periodic heartbeats
analogous to ingest.

## Out of Scope

- no CLI rendering work yet
- no generalized derive runner across all future jobs
- no UI live-monitoring endpoint

## Acceptance Criteria

- derive runs have their own persisted lifecycle records instead of being hidden
  behind logs only
- derive progress is persisted with phase, status, heartbeat timestamp, and
  numeric counters analogous to ingest
- the daily aggregate derive job uses the shared generic progress runtime rather
  than a new derive-only progress engine
- progress semantics for the daily aggregate job are explicitly documented in
  code and covered by tests
- ingest progress behavior remains stable after any required generalization of
  the shared runtime

## Notes

The main design objective is narrow reuse: one shared heartbeat/progress runtime
serving both ingest and derive, with separate run-lifecycle persistence where
the domain concepts differ.
