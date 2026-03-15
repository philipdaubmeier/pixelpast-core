# R-030-05 - Calendar Source and Event Persistence Lifecycle

## Goal

Persist calendar source candidates and canonical event candidates through the
same staged-ingest architectural seams already used by the photo connector.

This task should introduce the calendar-specific lifecycle and persistence
collaborators needed to make the new connector operational, while reusing the
generic staged runner and shared progress runtime where that reuse is natural.

## Dependencies

- `R-030-02`
- `R-030-04`

## Scope

### Add Calendar Event Persistence Behind Repositories

Introduce repository-backed calendar persistence components rather than placing
database logic in the connector.

At minimum, the persistence layer should be able to:

- resolve or create the canonical `Source` by `external_id`
- persist canonical `Event` rows for that source
- commit or rollback one open ingestion transaction

If no `EventRepository` exists yet, add one at the repository boundary instead
of persisting events inline from a service class.

### Use Source-Scoped Replacement for v1 Idempotency

The first calendar increment should stay idempotent without reshaping the event
schema.

The simplest acceptable approach is source-scoped full replacement:

- resolve the calendar source
- delete existing events for that source
- insert the newly transformed events for that source

This keeps repeated imports deterministic and avoids inventing a weak event
identity scheme before the product actually needs one.

### Introduce a Calendar Run Coordinator

Add a calendar-specific lifecycle collaborator analogous to the photo ingest
coordinator.

It should own:

- run creation
- initial progress state
- any source-level reconciliation needed before persistence

Do not move direct database writes into the connector.

### Reuse the Existing Staged Ingestion Runner

Calendar ingest should use the generic `StagedIngestionRunner` rather than
creating a second orchestration loop.

The natural staged unit here is one calendar document, with persistence
operating on one document candidate that contains:

- one source candidate
- many event candidates

### Define v1 Missing-From-Source Semantics Explicitly

Photo ingest reports informational `missing_from_source` counts. Calendar ingest
does not yet have delete-sync semantics beyond source-scoped replacement.

Define the v1 behavior explicitly, for example:

- report `missing_from_source = 0`
- avoid introducing fake source-missing calculations for events

### Define Duplicate Calendar Identity Behavior

If one run encounters two documents with the same calendar `external_id`, the
implementation must not silently persist both.

Define one deterministic v1 behavior and cover it with tests, such as:

- fail the later document as a transform or analysis error
- persist only the first document in deterministic discovery order

## Out of Scope

- no CLI source registration yet
- no attendee persistence
- no partial per-event upsert model

## Acceptance Criteria

- calendar persistence is implemented behind repository and lifecycle
  collaborators, not inline in the connector
- the calendar ingest path reuses the generic staged runner
- repeated imports of the same calendar document are idempotent through
  source-scoped event replacement
- a new calendar run coordinator exists and uses the shared progress runtime
- duplicate calendar external identifiers within one run are handled
  deterministically
- no changes are required to the canonical `Event` schema for v1 idempotency

## Notes

This task is where the calendar connector proves that the existing generic
staged-ingest shell is actually reusable beyond photos.
