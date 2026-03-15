# R-030-06 - Calendar CLI, Entrypoint, and End-to-End Tests

## Goal

Expose the calendar ingest connector through the same operational surfaces as
the existing photo ingest path and cover the full workflow with end-to-end
tests.

After this task, `pixelpast ingest calendar` should be a first-class supported
source using the shared runtime, shared progress reporting, and the new
calendar-specific collaborators introduced by the earlier subtasks.

## Dependencies

- `R-030-05`

## Scope

### Add Calendar Runtime Configuration

Extend shared settings with `PIXELPAST_CALENDAR_ROOT` and wire that setting into
the calendar ingestion service.

The service should validate that the setting is present when the `calendar`
source is invoked and should produce a clear error when it is missing.

### Add a Thin Calendar Ingestion Service

Create a `CalendarIngestionService` that mirrors the photo service role:

- read the configured root from shared settings
- create the run through the calendar lifecycle coordinator
- construct the calendar staged strategy and persistence scope
- delegate the actual orchestration to the generic staged runner

The service should be a composition root, not the home of parsing or database
logic.

### Register the Calendar Source in Ingestion Entrypoints and CLI

Extend the ingest entrypoint path so:

- `list_supported_ingest_sources()` includes `calendar`
- `run_ingest_source(source="calendar", ...)` runs the new service
- the CLI help and validation paths expose `calendar` as a supported source

Reuse the shared CLI progress rendering already in place. Do not introduce a
calendar-only terminal reporting path.

### Add End-to-End and Connector Tests

Add automated coverage for:

- direct `.ics` ingest from the Outlook fixture
- `.zip` ingest containing `.ics` content
- directory-root ingest across nested `.ics` and `.zip` files
- repeated execution idempotency
- source reuse through calendar external identity
- HTML description normalization
- duplicate calendar identity handling within one run
- the absence of created assets for calendar ingest

The tests should verify persisted canonical outcomes, not only service return
values.

## Out of Scope

- no UI work
- no derive-job changes
- no attendee features

## Acceptance Criteria

- `PIXELPAST_CALENDAR_ROOT` is part of shared runtime configuration
- `pixelpast ingest calendar` is available through the existing CLI and
  entrypoint path
- the calendar service is a thin composition root over staged runner,
  lifecycle, connector, and persistence collaborators
- the shared CLI progress reporter works for calendar ingest without a separate
  implementation
- automated tests cover direct-file, zip, directory, idempotency, and
  source-reuse behavior
- the tests confirm that calendar ingest persists events and sources but does
  not create assets

## Notes

This task should finish the connector as an operational ingest source without
broadening scope into attendee modeling or downstream UI work.
