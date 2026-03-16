# R-034-01 - Workdays Vacation Ingest Skeleton

## Goal

Introduce the structural ingest skeleton for a new `workdays_vacation` source
while reusing the staged-ingestion and shared-progress architecture already
established by the photo and calendar connectors.

This task is intentionally about the ingest shell and integration seams, not
about final spreadsheet parsing rules.

## Dependencies

- `R-022-08`
- `R-022-09`
- `R-025`
- `R-029`
- `R-034`

## Scope

### Connector Structure Direction

Add a new ingest package for `workdays_vacation` following the same explicit
responsibility split already used by the existing connectors:

- `connector`
- `contracts`
- `discovery`
- `fetch`
- `transform`
- `persist`
- `service`
- `staged`
- `progress`
- `lifecycle`

The implementation should favor real reuse of shared ingestion machinery rather
than copying photo-specific behavior.

### Source Registration Direction

The source should become a first-class ingest entry in the CLI and shared
entrypoint registry so it can participate in the existing ingest orchestration
flow.

The connector should be discoverable through the same top-level mechanisms that
already list and execute supported ingest sources.

### Intake Boundary Direction

At this stage, the connector only needs the filesystem-facing intake shell for
workbook-based imports.

It is acceptable for the exact spreadsheet fixture and column characterization
to remain deferred to the next subtask, but the connector skeleton should be
ready for one discovered workbook yielding:

- one canonical `Source`
- many canonical `Event` candidates

### Persistence Boundary Direction

The connector must preserve the existing architectural rule that direct
database interaction stays behind repository and lifecycle boundaries.

This task should therefore wire the new source into the staged ingest flow
without bypassing the established persistence seams.

## Out of Scope

- no finalized Excel parsing rules yet
- no fixture-specific column mapping yet
- no daily-aggregate logic yet
- no exploration API changes yet

## Acceptance Criteria

- a new `workdays_vacation` ingest package exists with the standard connector
  responsibility split
- the source is registered in the ingest entrypoint/CLI flow
- the implementation reuses staged orchestration and shared progress reporting
- the connector boundary is ready for workbook-based source discovery and
  transformation without writing directly to derived tables

## Notes

This task should establish the same architectural quality bar already expected
of other ingest connectors before fixture-specific parsing details are added.
