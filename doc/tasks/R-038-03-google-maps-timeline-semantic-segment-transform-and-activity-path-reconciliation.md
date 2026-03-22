# R-038-03 - Google Maps Timeline Semantic Segment Transform and Activity Path Reconciliation

## Goal

Transform the new Google Maps Timeline on-device `semanticSegments` structure
into canonical visit and movement event candidates.

This task is the semantic core of the connector. It should make the
interpretation rules explicit instead of burying them inside persistence logic.

## Dependencies

- `R-038-01`
- `R-038-02`

## Scope

### Parse the Supported Top-Level Export Object

Transform logic should parse the supported top-level object shape and extract:

- `semanticSegments`
- `rawSignals`
- `userLocationProfile`

For v1, only `semanticSegments` should influence emitted canonical events.

`rawSignals` and `userLocationProfile` may be observed for validation or warning
purposes, but must not produce canonical rows.

### Make Semantic Segment Kinds Explicit

Each semantic segment should be parsed into an explicit internal contract that
captures:

- segment kind
- start/end timestamps
- source order
- normalized lat/lon data where applicable
- kind-specific payload fields

The parser should treat the current supported kinds as:

- `visit`
- `activity`
- `timelinePath`

If other segment kinds appear in recent exports, such as `timelineMemory`, they
should be skipped with deterministic warning messages rather than crashing the
entire file import.

### Normalize Visits Into One Canonical Stay Event Per Time Window

The transform should resolve duplicate visit windows before canonical mapping.

When multiple visits share the same exact start/end timestamps:

- prefer the lowest `hierarchyLevel`
- then prefer the highest `topCandidate.probability`

The chosen visit should emit one canonical event candidate with:

- `type = "timeline_visit"`
- UTC-normalized `timestamp_start` / `timestamp_end`
- canonical latitude/longitude from `placeLocation`
- a non-empty human-readable title
- selected raw payload fields only

### Reconcile Activity Segments With Overlapping Timeline Paths

The transform must not emit standalone events for `timelinePath`.

Instead, for each `activity` segment, it should:

1. find every `timelinePath` segment whose own time window overlaps the activity
2. parse its individual point timestamps
3. keep only points within the activity window
4. add synthetic boundary points from `activity.start` and `activity.end`
5. sort the resulting path deterministically
6. remove exact duplicates when the same timestamp/coordinate pair appears
   multiple times

This should produce one canonical activity event candidate with:

- `type = "timeline_activity"`
- UTC-normalized `timestamp_start` / `timestamp_end`
- `Event.latitude` / `Event.longitude` from `activity.start`
- a non-empty human-readable title from the top activity candidate
- movement detail stored in `raw_payload.pathPoints`

### Make the Activity Clipping Rule Executable

Add tests that explicitly pin the recommended path-clipping interpretation:

- path points outside the activity window are excluded
- overlapping path windows may contribute points to one activity
- consecutive activities may receive different subsets from the same broader
  path window
- an activity with no surviving path points still emits an event using only the
  boundary locations

### Keep Raw Payloads Selective

The transform should not dump the full original segment into canonical
`raw_payload`.

Instead, it should persist only the selected fields needed for provenance and
future route rendering, for example:

- place or activity classification
- confidence values
- selected boundary coordinates
- clipped path points
- distance in meters

## Out of Scope

- no repository persistence yet
- no delete sync yet
- no `rawSignals` import
- no `userLocationProfile` import
- no route geometry table

## Acceptance Criteria

- transform logic parses supported on-device semantic-segment kinds into
  explicit internal contracts
- duplicate visit windows are normalized to one canonical visit event
- `timelinePath` does not emit its own canonical event rows
- each activity event receives only the path points that fall inside its own
  time window
- activities still import when no clipped path points remain
- emitted event candidates have non-empty titles suitable for current day-detail
  APIs
- unsupported future segment kinds are skipped deterministically rather than
  crashing the whole import

## Notes

The activity-plus-clipped-path behavior is an inference from recent community
analysis of the new export and from observed Google Timeline rendering, not from
an official Google schema document. That inference should be made explicit in
tests and comments where needed.
