# R-022-06 - Photo Import Run Lifecycle Extraction

## Goal

Extract source and import-run lifecycle responsibilities from
`ingestion/photos/service.py`.

Right now the service still owns non-trivial operational persistence concerns
that are separate from both canonical asset persistence and connector logic:

- source lookup or creation
- import-run creation
- initial progress payload construction
- missing-from-source inspection

These responsibilities should become explicit collaborators.

## Dependencies

- `R-022-05`

## Scope

### Introduce an Import-Run Lifecycle Collaborator

Create a photo-ingest lifecycle component, for example:

- `PhotoImportRunCoordinator`
- `PhotoIngestionRunStore`

It should own:

- source lookup or creation for `Photos` / `photos`
- import-run creation for mode `full`
- initial persisted progress payload creation

### Centralize Initial Progress State

The zeroed progress payload should have one explicit home rather than being
hand-assembled in the service.

This task should define one authoritative initializer for the persisted progress
shape used at run start.

### Move Missing-From-Source Inspection

The informational count of already-known assets missing from the current source
directory should move out of the main orchestration method and into the
lifecycle or source-state collaborator.

The behavior must remain unchanged:

- informational only
- no delete synchronization
- no asset deactivation

### Keep Operational Semantics Stable

The extracted lifecycle component must preserve:

- source name `Photos`
- source type `photos`
- root-path configuration persistence
- import-run status initialization
- compatibility with the existing progress tracker

## Out of Scope

- no heartbeat redesign yet
- no staged base runner yet
- no change to source naming or import-run schema

## Acceptance Criteria

- tests covering completed, failed, and partial-failure runs still pass
- `missing_from_source_count` behavior remains unchanged
- initial import-run progress state is created from one explicit source of truth
- `PhotoIngestionService` no longer owns source/import-run bootstrapping and
  missing-from-source query details

## Notes

This task keeps operational state management separate from both connector logic
and canonical asset persistence, which is necessary before introducing any
shared runner.
