# R-036-05 - Spotify CLI, Entrypoint, Progress, and End-to-End Tests

## Goal

Expose the Spotify ingest connector through the same operational surfaces as
the existing connectors and cover the full workflow with end-to-end tests.

After this task, `pixelpast ingest spotify` should be a first-class supported
source using the shared runtime, shared progress reporting, and the Spotify
collaborators introduced by the earlier subtasks.

## Dependencies

- `R-036-04`

## Scope

### Add a Thin Spotify Ingestion Service

Create a `SpotifyIngestionService` that mirrors the role of the existing ingest
services:

- read the configured root from shared settings
- create the run through the Spotify lifecycle coordinator
- construct the Spotify staged strategy and persistence scope
- delegate orchestration to the generic staged runner

The service should remain a composition root rather than becoming the home of
JSON parsing or database logic.

### Register the Spotify Source in Entrypoints and CLI

Extend the ingest entrypoint path so:

- `list_supported_ingest_sources()` includes `spotify`
- `run_ingest_source(source="spotify", ...)` runs the new service
- the CLI help and validation paths expose `spotify` as a supported source

Reuse the shared CLI progress renderer already in place. Do not introduce a
Spotify-only terminal reporting path.

### Define Spotify Progress Reporting

Add a Spotify progress tracker that reports meaningful connector progress using
the shared progress runtime.

At minimum, it should make room for counters such as:

- discovered document count
- loaded document count
- analyzed row count
- persisted source count
- persisted event count
- error count

The exact payload can follow the established connector-specific pattern, but it
must remain compatible with the generic CLI progress path.

### Add End-to-End Coverage

Add automated tests for:

- direct-file ingest
- recursive-directory ingest with multiple JSON files
- repeated execution idempotency
- account-level merging across multiple files for the same username
- multiple-account behavior when different usernames appear in the input set
- canonical mapping of title, timestamps, type, and selected raw payload
- absence of created assets
- progress snapshots flowing through the shared CLI-compatible path

The tests should verify persisted canonical outcomes, not only service return
values.

## Out of Scope

- no UI changes
- no derive-job changes yet
- no Spotify Web API integration

## Acceptance Criteria

- `pixelpast ingest spotify` is available through the existing CLI and
  entrypoint path
- the Spotify service is a thin composition root over staged runner,
  lifecycle, connector, and persistence collaborators
- the shared CLI progress reporter works for Spotify ingest without a separate
  implementation
- automated tests cover single-file, multi-file, multi-account, idempotency,
  and no-asset behavior
- the tests confirm that Spotify ingest persists events and sources but does
  not create assets

## Notes

This task should finish the connector as an operational ingest source without
broadening scope into derive behavior or remote metadata enrichment.
