# R-030-07 - Calendar Missing Event Reconciliation and Delete Sync

## Goal

Extend the calendar ingest so repeated imports can detect events that were
previously persisted for an existing calendar source but are no longer present
in the current ICS input, report them as `missing_from_source`, and delete them
from the database during persistence.

This task closes the remaining gap in the calendar ingest lifecycle between
"known unchanged events" and "events removed from the source calendar".

## Dependencies

- `R-030-05`
- `R-030-06`

## Scope

### Reconcile Source-Scoped Existing Events Before Persistence

When an ICS document resolves to an already existing calendar `Source`, the
calendar ingest flow should compare the newly transformed event candidates
against the events currently persisted for that source before the persistence
phase writes changes.

The reconciliation must identify at least these buckets:

- `created`
- `updated`
- `unchanged`
- `missing_from_source`

The comparison should be scoped only to events belonging to the resolved
calendar source.

### Define Missing Event Behavior Explicitly

If an event exists in the database for the resolved calendar source but no
matching event exists in the current ICS payload, that event must be treated as
`missing_from_source`.

For this task, `missing_from_source` means:

- the event is counted in ingest summary reporting
- the event is deleted from the database in the same persistence lifecycle

Example target behavior:

- first import: calendar with `X-WR-RELCALID:123` and 10 events
- second import: same calendar identity, now only 9 events in the ICS
- result:
  - 9 events are classified according to content comparison, e.g. `unchanged`
  - 1 event is classified as `missing_from_source`
  - the missing event is removed from persisted canonical events for that source

### Keep Reconciliation Inside Lifecycle and Persistence Boundaries

The missing-event detection and delete-sync behavior must live in the same
architectural seams already used by staged ingest:

- source and event lookup behind repositories
- reconciliation in calendar-specific lifecycle or persistence collaborators
- connector responsibilities limited to discovery, fetch, and transformation

Do not move direct database logic into the connector or parsing layer.

### Extend CLI Summary Reporting

The CLI summary and shared ingest reporting should expose the new
`missing_from_source` outcome for calendar ingest so repeated runs make deleted
source events visible to the operator.

The reporting should remain aligned with the shared progress and summary model
rather than introducing a calendar-only reporting path.

### Cover Reconciliation with Tests

Add automated coverage for at least:

- repeated ingest of the same calendar with no changes
- repeated ingest where one previously persisted event is removed from the ICS
- repeated ingest where removed events are counted as `missing_from_source`
- repeated ingest where missing events are actually deleted from the database
- preservation of source reuse through `Source.external_id`

The tests should verify both persisted canonical state and reported ingest
summary outcomes.

## Out of Scope

- no attendee reconciliation
- no soft-delete model for canonical events
- no cross-source reconciliation
- no broader event identity redesign beyond what calendar ingest already uses

## Acceptance Criteria

- repeated calendar ingest compares current ICS events against previously
  persisted events for the resolved source before persistence writes final state
- events missing from the current ICS input are classified as
  `missing_from_source`
- `missing_from_source` calendar events are deleted from the database during the
  same ingest run
- unchanged events are not duplicated
- CLI ingest summaries expose `missing_from_source` for calendar runs
- automated tests cover the removed-event reconciliation path end to end

## Notes

`R-030-05` explicitly chose source-scoped replacement as the simplest v1
idempotency model. This task refines that behavior into explicit source-scoped
reconciliation so the operator can see which events disappeared from the source
instead of only observing the final replaced state.
