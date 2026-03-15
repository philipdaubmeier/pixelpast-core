# R-030 - Calendar Event Ingest v1

## Goal

Introduce the first calendar ingestion connector for PixelPast.

Unlike the photo connector, this ingest path creates canonical `Event` rows and
does not create `Asset` rows. The first increment should import `.ics` calendar
exports from the local filesystem, including zipped `.ics` files, and map
calendar entries into the existing canonical event model without reshaping the
event schema.

This task series must follow the responsibility split already established by the
photo ingest work wherever that reuse is justified:

- staged orchestration
- shared progress reporting
- lifecycle coordination
- thin connector facade
- persistence behind repository boundaries

It must not copy photo-specific abstractions blindly. Calendar ingestion has one
important structural difference: one discovered calendar document yields one
calendar source plus many canonical events.

## Dependencies

- `R-022-08`
- `R-022-09`
- `R-025`
- `R-029`

## Scope

This task series should introduce a new `calendar` ingest source with the
following first-version behavior:

- `PIXELPAST_CALENDAR_ROOT` accepts:
  - a direct `.ics` file
  - a `.zip` file containing one or more `.ics` files
  - a directory, in which case all nested `.ics` and `.zip` files are processed
    recursively
- zipped `.ics` inputs should be processed in memory and should not be extracted
  to temporary files on disk
- each ingested calendar document becomes or reuses one canonical `Source`
- each `VEVENT` becomes one canonical `Event`
- no assets are created
- invited attendees, `EventPerson`, tags, and location mapping remain out of
  scope for v1

### Canonical Mapping Direction

For the first increment, calendar events must map into the existing canonical
model as follows:

- `DTSTART` -> `Event.timestamp_start` in UTC
- `DTEND` -> `Event.timestamp_end` in UTC
- `SUMMARY` -> `Event.title`, truncated to 220 characters plus `...` when needed
- `X-ALT-DESC`
  - plaintext values map directly to `Event.summary`
  - HTML values must be converted to plaintext with markup removed and images
    discarded before storing the remaining text in `Event.summary`

### Source Identity Direction

Each calendar document must correspond to one canonical `Source` of type
`calendar`.

The source identity should come from the calendar-level external identifier
header present in the export. The provided Outlook fixture uses
`X-WR-RELCALID`; the original request's `X-WR-RECALID` appears to refer to that
same field.

This task series should therefore add explicit `Source.external_id` support and
make that field unique, so repeated imports can reuse the same calendar source.

### Architectural Direction

The implementation should reuse the existing generic ingestion shell where that
reuse is real:

- keep `discover -> fetch -> transform -> persist` explicit
- reuse the staged ingestion runner rather than creating a second orchestration
  loop
- reuse the shared progress engine and CLI reporting
- follow the photo ingest folder split as the design reference

At the same time, do not force calendar-specific concerns such as zip-member
stream handling or multi-event calendar persistence into photo-specific modules.

## Subtasks

- `R-030-01`
  - define calendar ingest contracts and characterize the Outlook fixture
- `R-030-02`
  - extend canonical source identity with `external_id`
- `R-030-03`
  - implement calendar document discovery and zip-backed intake boundaries
- `R-030-04`
  - transform parsed ICS data into canonical calendar event candidates
- `R-030-05`
  - persist calendar sources and events through staged ingestion lifecycle seams
- `R-030-06`
  - wire CLI and entrypoints, and cover the end-to-end ingest path with tests

## Out of Scope

- no attendee ingestion yet
- no `EventPerson` population yet
- no tag extraction from calendars
- no location parsing into latitude / longitude
- no delete synchronization for removed calendar files beyond source-scoped event
  replacement
- no schema changes to `Event`, `Asset`, `Tag`, or person association tables
  beyond the explicit `Source.external_id` addition

## Acceptance Criteria

- a documented task series exists for the first calendar ingest connector
- the series explicitly states that calendar ingest creates canonical events and
  not assets
- each calendar import is idempotent, i.e. if a file with the same calendar uuid
  is read again all events are related to the same source entry. also, if events
  with the same UID are read these are replaced, when events with the same UID
  have the same contents, these events are not imported as duplicates. Overall,
  if a calendar ICS with exact same contents are read twice, the database does
  not change at all.
- the series explicitly states that `.ics`, `.zip`, and recursive directory
  intake are required
- the series explicitly requires in-memory zip handling without writing expanded
  ICS files to disk
- the series explicitly requires source reuse through a new unique
  `Source.external_id`
- the series explicitly requires reuse of the staged ingest and shared progress
  architecture already established by the photo ingest path

## Notes

The provided fixture at `test/assets/outlook_cal_export_test_fixture.ics` should
be treated as the first characterization anchor for Outlook-export behavior,
including timezone metadata, calendar-level source headers, and HTML
descriptions.
