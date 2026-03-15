# R-030-03 - Calendar Document Discovery and Zip Intake

## Goal

Add calendar-specific discovery and fetch components that can accept the
configured calendar root as:

- a single `.ics` file
- a single `.zip` file containing `.ics` files
- a directory containing nested `.ics` and `.zip` files

This task should mirror the concern split of the photo connector while staying
honest about the different input shape.

## Dependencies

- `R-030-01`

## Scope

### Introduce a Dedicated Calendar Document Discoverer

Create a discovery component responsible for:

- validating `PIXELPAST_CALENDAR_ROOT`
- accepting either file or directory roots
- recursively traversing directories
- filtering supported input types:
  - `.ics`
  - `.zip`
- producing deterministic processing order
- emitting per-document discovery progress

The discovered unit should be a calendar document descriptor, not a bare path,
because zip-backed `.ics` members need archive context.

### Separate Discovery from Content Loading

Calendar discovery should only identify ingestible documents.

The actual loading of raw ICS bytes or text should live in a separate fetch /
read collaborator so the staged ingest structure stays visible:

- discover document descriptors
- fetch raw ICS content
- transform parsed ICS content into canonical candidates

### Require In-Memory Zip Handling

When a `.zip` input is encountered, `.ics` members must be read directly from
the archive stream and processed in memory.

Do not:

- extract `.ics` members to temporary files
- write expanded content to the repository
- rely on side-effectful filesystem staging

### Define Duplicate Discovery Semantics

If discovery encounters multiple calendar documents that would later resolve to
the same calendar external identifier, later tasks must have enough descriptor
information to surface a deterministic duplicate-document error rather than
accidentally processing both as independent calendars.

This task does not need to resolve that duplication yet, but it should preserve
enough origin metadata for later stages to do so.

## Out of Scope

- no ICS parsing yet
- no source or event persistence yet
- no CLI source registration yet

## Acceptance Criteria

- a calendar discovery component exists with explicit support for file, zip, and
  recursive directory roots
- supported documents are discovered in deterministic order
- zip-backed `.ics` documents are represented without requiring extraction to
  disk
- discovery and raw-content loading are split into separate concerns
- the resulting document descriptor shape carries enough origin metadata for
  progress reporting, config persistence, and duplicate-source detection

## Notes

This task should borrow the clarity of `PhotoFileDiscoverer`, not its exact
implementation assumptions. Photo discovery only sees ordinary files; calendar
discovery must also represent archive members.
