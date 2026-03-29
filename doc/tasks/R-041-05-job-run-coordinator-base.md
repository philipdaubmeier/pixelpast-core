# R-041-05 - Job Run Coordinator Base

## Goal

Unify the repeated job-run bootstrap logic across ingestion lifecycle
coordinators and the derive lifecycle coordinator.

Several coordinators currently repeat the same steps:

- create a session
- create a job run with initial phase and zeroed progress payload
- commit and return the new run id

Photos and Lightroom additionally bootstrap source state for asset-oriented
ingestion. This task should extract the shared job-run shell without changing
source semantics or run payload behavior.

## Dependencies

- none

## Scope

### Introduce a Shared Job-Run Bootstrap Base

Create a reusable coordinator base or helper for job-run creation.

It should centralize the repeated mechanics for:

- session handling
- initial progress payload construction
- job-run record creation
- commit and return semantics

Allow coordinator-specific hooks for:

- root-path payload enrichment
- source bootstrap before run creation
- custom source-id lookup helpers where needed

### Preserve Source-Specific Lifecycle Behavior

Do not collapse all lifecycle coordinators into one generic object with stringly
typed switches.

Connector-specific coordinator classes should remain explicit where they add
real behavior, especially for:

- photo source creation and source-id lookup
- Lightroom source external-id and source-name bootstrapping

### Keep Existing Job-Run Metadata Stable

Do not change:

- job names
- job types
- initial phases
- persisted mode values
- root-path payload fields already written today

The refactor should stay behavior-preserving.

## Out of Scope

- no schema changes
- no merge of ingest and derive into one domain concept
- no source-identity redesign

## Acceptance Criteria

- repeated job-run bootstrap mechanics are centralized in one shared base or
  helper
- connector-specific lifecycle coordinators remain explicit where they add real
  behavior
- job-run metadata and source-bootstrapping behavior remain unchanged

## Notes

This task is about extracting the operational shell, not about flattening the
important distinction between ingest and derive responsibilities.
