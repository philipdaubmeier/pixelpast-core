# R-030-04 - ICS Parsing and Calendar Event Transformation

## Goal

Turn raw calendar document content into canonical calendar source candidates and
event candidates using a robust ICS parsing library.

This is the task where the calendar connector becomes semantically useful:
calendar-level metadata is extracted once, `VEVENT` entries are normalized, and
the existing canonical `Event` model is populated without introducing calendar-
specific schema.

## Dependencies

- `R-030-01`
- `R-030-02`
- `R-030-03`

## Scope

### Choose a Robust ICS Parsing Library

Use a mature Python ICS parser that can correctly handle:

- Outlook-style timezone declarations
- timezone-bearing `DTSTART` / `DTEND`
- date-only and datetime event values
- common ICS edge cases such as folded lines and optional properties

The library choice should be justified by behavior, not fashion. The tests must
prove the chosen parser handles the provided Outlook export correctly.

### Extract Calendar-Level Source Metadata

Transform each parsed calendar document into one source candidate containing:

- `external_id` from the calendar identifier header observed in the document
- `name` from `X-WR-CALNAME`
- `type = "calendar"`
- config derived from the original input descriptor

If the required calendar identifier header is absent, fail the document
deterministically rather than inventing a synthetic source identity.

### Transform `VEVENT` Entries into Canonical Event Candidates

Each supported `VEVENT` should map into an event candidate with the following
v1 rules:

- `DTSTART` -> UTC `timestamp_start`
- `DTEND` -> UTC `timestamp_end`
- `SUMMARY` -> `title`
- `X-ALT-DESC` -> `summary`
- `type = "calendar"`
- `source_id` remains unresolved until persistence

Keep `latitude`, `longitude`, and tag/person associations unset in v1.

### Normalize Text Fields Deterministically

Apply the requested text handling rules explicitly:

- truncate `SUMMARY` to 220 characters and append `...` when truncation occurs
- if `X-ALT-DESC` is plaintext, store it directly
- if `X-ALT-DESC` is HTML:
  - parse it with a dedicated HTML parser
  - remove markup
  - ignore images
  - keep only remaining plaintext content

### Preserve Enough Source-Native Event Metadata for Reconciliation

Because the canonical `Event` schema does not gain an external identifier in
this increment, the transform output should still preserve enough source-native
metadata in the candidate payload for later persistence and debugging, such as:

- calendar event UID
- original source properties needed for traceability

This metadata should stay within raw payload structures rather than driving a
new schema extension.

## Out of Scope

- no attendee extraction yet
- no event-person linking yet
- no location parsing
- no persistence transaction behavior yet

## Acceptance Criteria

- one parsed calendar document yields one source candidate and many event
  candidates
- the chosen ICS library correctly parses the provided Outlook fixture
- timestamps are normalized to UTC before reaching persistence
- HTML `X-ALT-DESC` values are converted into plaintext summaries without image
  content
- title truncation is deterministic and covered by tests
- event candidates preserve source-native metadata in raw payloads without
  extending the canonical event schema

## Notes

This task should keep parsing and transformation separate from repository work.
The output of this task is a canonical candidate graph, not committed database
rows.
