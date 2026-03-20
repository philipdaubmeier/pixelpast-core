# R-036-01 - Spotify Ingest Contracts and Fixture Characterization

## Goal

Define the public contracts and behavioral baseline for Spotify streaming
history ingest before persistence and CLI wiring are added.

The connector will need to handle multiple JSON documents, one account-level
canonical source, and many canonical event candidates. That shape should be
made explicit in tests and contracts before the implementation spreads those
assumptions across the service and persistence layers.

## Dependencies

- `R-022-08`

## Scope

### Introduce Spotify-Specific Contracts

Define the small set of Spotify-ingest contracts needed by later tasks, for
example:

- discovered streaming-history document descriptors
- loaded streaming-history document payloads
- parsed Spotify stream row contracts
- account-level source candidates
- canonical Spotify event candidates
- document-level transform errors
- final Spotify ingestion result

These contracts should reflect the real unit boundaries of the connector:

- many discovered documents
- one or more usernames found in those documents
- one canonical source per username
- many canonical events per source

### Characterize Realistic Takeout Fixtures

Add tests and local fixtures that pin down the first expected behaviors from
Spotify takeout data:

- JSON array document shape
- row field presence and nullability
- `ts` as the stream stop timestamp in UTC
- `ms_played` as the played duration in milliseconds
- track rows with track metadata and track URI
- episode rows with episode URI and missing track metadata

At least one fixture should cover multiple rows, and at least one focused test
should cover title-empty behavior when the artist/title pair is unavailable.

### Define v1 Mapping Semantics Explicitly

Before persistence is implemented, make the intended canonical mapping behavior
precise in tests and contracts:

- `Event.type` is always `music_play`
- `Event.timestamp_end` is parsed from `ts` as a UTC datetime
- `Event.timestamp_start` is `timestamp_end - ms_played`
- `Event.title`
  - uses `"{artist} - {title}"` when both fields are present after trimming
  - remains empty in v1 when one or both fields are unavailable
- `Event.summary` remains empty in v1
- canonical `raw_payload` contains only the selected subset of Spotify fields

### Define Account Identity Baseline

Pin down the v1 expectation that username drives canonical source identity.

Tests should make explicit that repeated rows from the same normalized username
map to the same account-level source identity candidate.

## Out of Scope

- no database persistence yet
- no runtime settings or CLI wiring yet
- no daily-aggregate derive changes yet

## Acceptance Criteria

- Spotify-ingest contract types exist for discovery, parsed rows, transform
  output, and final result reporting
- automated tests characterize local Spotify takeout fixtures rather than only
  mocked dictionaries
- tests explicitly pin UTC parsing and start/end timestamp derivation
- tests explicitly pin the selected canonical `raw_payload` field subset
- tests explicitly pin the title-empty behavior for rows without a usable
  artist/title pair
- the contracts model many documents producing one or more account-level source
  candidates and many canonical event candidates

## Notes

This task is intentionally narrow. Its purpose is to prevent later Spotify
implementation work from hard-coding account grouping and row mapping semantics
without tests.
