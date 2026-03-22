# R-038-05 - Google Maps Timeline Missing Event Reconciliation and Delete Sync

## Goal

Extend the Google Maps Timeline ingest so repeated imports of the same export
file can detect previously persisted source events that are no longer present in
the current JSON payload, report them as `missing_from_source`, and delete them
from the database during the same ingest run.

## Dependencies

- `R-038-04`

## Scope

### Reconcile the Current Export Against the Existing Source Event Set

When the configured export file resolves to an already existing canonical
source, the ingest flow should compare the newly transformed event candidates
against the events currently persisted for that source before final persistence.

The reconciliation must identify at least these buckets:

- `created`
- `updated`
- `unchanged`
- `missing_from_source`

### Define Missing Event Behavior Explicitly

If an event exists in the database for the resolved Google Maps Timeline source
but no matching event exists in the current export file, that event must be
treated as `missing_from_source`.

For this task, `missing_from_source` means:

- the event is counted in ingest summary reporting
- the event is deleted from the database in the same persistence lifecycle

Example target behavior:

- first import: one export file produces 20 canonical events
- second import: same file path, changed contents now produce 19 events
- result:
  - 19 events are classified as inserted, updated, or unchanged
  - 1 event is classified as `missing_from_source`
  - the missing event is removed from persisted canonical events for that source

### Keep Reconciliation Inside Lifecycle and Persistence Boundaries

Missing-event detection and delete sync must live in the same architectural
seams already used by staged ingest:

- source lookup behind repositories
- event comparison behind repositories
- connector responsibilities limited to discovery, fetch, and transformation

Do not move direct database logic into the connector or parsing layer.

### Cover Delete Sync With Tests

Add automated coverage for at least:

- repeated ingest of the same export with no changes
- repeated ingest where one previously persisted visit disappears
- repeated ingest where one previously persisted activity disappears
- repeated ingest where removed events are counted as `missing_from_source`
- repeated ingest where missing events are actually deleted from the database

## Out of Scope

- no reconciliation for whole missing export files, because v1 is file-scoped
- no soft-delete model for canonical events
- no multi-device merge behavior

## Acceptance Criteria

- repeated import of the same Google Maps Timeline export file compares the
  current transformed event set against the source's persisted events
- events missing from the current export are classified as
  `missing_from_source`
- `missing_from_source` events are deleted during the same ingest run
- unchanged events are not duplicated
- automated tests cover the removed-event reconciliation path end to end

## Notes

The file-scoped connector boundary is what makes this task clean. Whole missing
document reconciliation is intentionally deferred by not supporting directory
intake in v1.
