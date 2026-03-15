# R-030-01 - Calendar Ingest Contracts and Fixture Characterization

## Goal

Define the public contracts and behavioral baseline for the new calendar ingest
connector before persistence and service wiring are added.

The photo ingest refactoring started with characterization and explicit
contracts. Calendar ingest should do the same, because the first input fixture
already demonstrates Outlook-specific headers, timezone declarations, and
`X-ALT-DESC` HTML payloads that can easily drift into ad-hoc logic if the
behavior is not pinned down first.

## Dependencies

- `R-022-08`

## Scope

### Introduce Calendar-Specific Contracts

Define the small set of calendar-ingest contracts needed by later tasks, for
example:

- discovered calendar document descriptors
- parsed calendar document metadata
- canonical calendar event candidates
- calendar document level transform errors
- final calendar ingestion result

These contracts should reflect the actual unit of work for calendar ingest:

- one discovered document
- one canonical source candidate
- many event candidates

Do not shape them around photo assets.

### Characterize the Outlook Fixture

Add tests that read `test/assets/outlook_cal_export_test_fixture.ics` and pin
down the first expected behaviors from a real export:

- calendar-level name header
- calendar-level external identifier header
- timezone-bearing `DTSTART` and `DTEND`
- `SUMMARY`
- `X-ALT-DESC;FMTTYPE=text/html`

The tests should make the observed header names explicit.

### Define v1 Mapping Semantics Explicitly

Before persistence is implemented, make the intended canonical mapping behavior
precise in tests and contracts:

- title truncation rule:
  - keep the first 220 characters of `SUMMARY`
  - append `...` when truncation happens
- summary extraction rule:
  - plaintext `X-ALT-DESC` is stored as-is
  - HTML `X-ALT-DESC` is converted to plaintext with markup removed and images
    ignored
- timestamp rule:
  - calendar timestamps are normalized to UTC datetimes before persistence

If the fixture does not yet cover one branch, add focused synthetic tests for
that branch alongside the fixture-based characterization.

### Document the Intended Reuse Boundary

Make the calendar document unit explicit enough that later tasks can plug it
into the existing `StagedIngestionRunner` without redesigning that generic
runner.

## Out of Scope

- no database schema changes yet
- no CLI or entrypoint wiring yet
- no final persistence implementation yet

## Acceptance Criteria

- calendar-ingest contract types exist for document discovery, transform output,
  and final result reporting
- automated tests characterize the Outlook fixture rather than relying only on
  mocked dictionaries
- the tests explicitly pin the observed calendar identifier header name from the
  fixture
- title truncation, summary normalization, and UTC timestamp normalization are
  documented in executable tests or contract-focused tests
- the contracts model one calendar document producing one source candidate and
  many event candidates

## Notes

This task is intentionally small. Its main value is to prevent the later
calendar implementation from smuggling persistence assumptions into parsing and
transform code.
