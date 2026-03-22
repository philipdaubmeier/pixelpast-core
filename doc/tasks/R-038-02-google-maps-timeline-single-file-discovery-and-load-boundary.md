# R-038-02 - Google Maps Timeline Single-File Discovery and Load Boundary

## Goal

Implement the discovery and raw-load boundary for one Google Maps Timeline
on-device export file.

The current mobile export use case is naturally single-file. The connector
should keep that boundary explicit instead of pretending this is the same
multi-document intake problem as calendar or Spotify.

## Dependencies

- `R-038-01`

## Scope

### Validate One Supported Export Root

The connector should accept exactly one configured root path and validate that
it is:

- present
- a filesystem file
- a `.json` document

The discovery layer should reject unsupported roots with clear error messages,
for example:

- missing path
- directory path
- non-JSON file

### Keep Discovery Explicit Even for One File

Even though the connector is file-scoped, it should still expose a small
dedicated discovery component so it fits the existing staged-ingestion
architecture cleanly.

The discovery result should therefore still be modeled as a deterministic set
of discovered units, even if that set contains exactly one file.

### Load Raw Export Text Through a Dedicated Fetch Boundary

The connector should load the raw file text through a dedicated fetch/load
component rather than parsing JSON directly inside discovery or service wiring.

This boundary should:

- read the file as UTF-8 text
- preserve the export origin label for later errors
- keep JSON parsing in the transform stage rather than in discovery

## Out of Scope

- no JSON semantic parsing yet
- no source identity yet
- no canonical persistence yet

## Acceptance Criteria

- a dedicated discovery component validates one supported JSON export file
- a dedicated fetch/load component returns raw text for that file
- directory roots and non-JSON roots fail with clear messages
- the connector still fits the existing staged ingest shell despite the
  single-file scope

## Notes

The point of this task is architectural cleanliness, not feature breadth.

Restricting v1 to one file keeps delete-sync semantics honest and avoids a
second reconciliation problem for whole missing export files.
