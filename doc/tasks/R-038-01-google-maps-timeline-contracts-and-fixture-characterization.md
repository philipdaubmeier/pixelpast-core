# R-038-01 - Google Maps Timeline Contracts and Fixture Characterization

## Goal

Define the public contracts and behavioral baseline for Google Maps Timeline
on-device ingest before persistence and CLI wiring are added.

This task should make the shape of the new export explicit in tests and
contracts so later work does not spread ad-hoc assumptions about segment
ordering, coordinate encoding, or timestamp handling across the connector.

## Dependencies

- `R-022-08`

## Scope

### Introduce Google-Maps-Timeline-Specific Contracts

Define the small set of ingest contracts needed by later tasks, for example:

- discovered export document descriptors
- loaded export payload contracts
- parsed semantic-segment contracts
- document-level source candidates
- canonical event candidates
- transform errors
- final ingestion result

The contracts should reflect the actual shape of this connector:

- one discovered JSON export file
- one canonical source candidate
- many semantic segments
- many canonical event candidates

### Characterize the Provided On-Device Fixture

Add tests and local characterization assertions for
`test/assets/googlemaps_timeline_test_fixture.json`.

The characterization should at least pin:

- top-level JSON object shape
- presence of `semanticSegments`
- presence of `rawSignals`
- presence of `userLocationProfile`
- one `visit` segment example
- one `timelinePath` segment example
- one `activity` segment example
- field names and nullability used by the checked-in fixture

### Make Timestamp and Coordinate Parsing Explicit

Tests should pin the first expected parsing rules:

- ISO 8601 timestamps with explicit offsets are accepted and normalized to UTC
- coordinate strings such as `"52.5252309°, 13.3683630°"` are parsed into float
  latitude/longitude pairs
- parser logic is tolerant of degree-symbol encoding artifacts such as `Â°`

### Explicitly Call Out the Fixture Time Mismatch

The provided anonymized fixture should be documented as structurally useful but
insufficient for path-clipping assertions.

Tests should explicitly capture that:

- the `timelinePath` segment is dated `2026-01-01`
- its contained point timestamps are dated `2025-03-25`

Later transform tests must therefore use an additional synthetic payload with
aligned timestamps.

### Define Format Rejection Baseline

Before persistence is implemented, the connector should already make explicit
what it does not support in v1.

Tests should pin clear rejection for at least:

- legacy `timelineObjects` exports
- `Records.json`-style `locations` exports
- non-object JSON payloads

## Out of Scope

- no repository persistence yet
- no CLI wiring yet
- no delete sync yet

## Acceptance Criteria

- Google-Maps-Timeline-specific contract types exist for discovery, parsed
  export payload, transform output, and final result reporting
- automated tests characterize the checked-in on-device fixture rather than only
  mocked dictionaries
- tests explicitly pin UTC normalization and coordinate parsing rules
- tests explicitly pin that the checked-in fixture cannot be used alone for
  activity-path clipping behavior
- tests explicitly pin that old Takeout top-level shapes are rejected in v1

## Notes

This task should stay narrow. Its purpose is to prevent later implementation
work from guessing at the new export shape without executable characterization.
