# R-038 - Google Maps Timeline On-Device Ingest v1

## Goal

Introduce a first Google Maps Timeline ingestion connector for the current
on-device export format produced by the Google Maps app.

Unlike the old Google Takeout location-history formats, the new export is a
single JSON document stored on the device and exported from the mobile app. The
first connector increment should explicitly target that new object-shaped export
with top-level sections such as `semanticSegments`, `rawSignals`, and
`userLocationProfile`.

This series should reuse the ingestion architecture already established by the
existing connectors wherever that reuse is real:

- staged orchestration
- shared progress reporting
- lifecycle coordination
- thin connector facade
- persistence behind repository boundaries

The implementation should remain split into focused Python modules such as:

- `contracts.py`
- `discovery.py`
- `fetch.py`
- `transform.py`
- `persist.py`
- `lifecycle.py`
- `progress.py`
- `staged.py`
- `connector.py`
- `service.py`

## Dependencies

- `R-022-08`
- `R-022-09`
- `R-025`
- `R-029`

## Scope

This task series should introduce a new `google_maps_timeline` ingest source
with the following first-version behavior:

- `PIXELPAST_GOOGLE_MAPS_TIMELINE_ROOT` must point to one exported `.json` file
- the connector must reject the legacy web Takeout formats such as
  `timelineObjects` and `locations`
- one exported JSON document becomes one canonical `Source`
- canonical `Source.type` should be `google_maps_timeline`
- canonical visit events should use `Event.type = "timeline_visit"`
- canonical movement events should use `Event.type = "timeline_activity"`
- no canonical `Asset` rows are created
- `rawSignals` and `userLocationProfile` are ignored in v1

### File-Scoped Intake Direction

The connector should intentionally be file-scoped in v1.

The new on-device export is naturally a single-document export. Restricting v1
to one configured JSON file keeps source identity and delete synchronization
clean:

- repeated import of the same file path can reuse the same canonical source
- `missing_from_source` can be defined against the current contents of that one
  file
- directory-level reconciliation for whole missing export files is avoided until
  there is a real product need for multi-export intake

### Semantic Interpretation Direction

The `semanticSegments` array should be treated as the only import source in v1.

Recommended interpretation:

- `visit`
  - a semantic place-stay segment that should map to one canonical event
- `activity`
  - a semantic movement segment that should map to one canonical event
- `timelinePath`
  - a geometry stream for movement detail that should not create a standalone
    canonical event

Instead, `timelinePath` points should be attached to the overlapping
`activity` event as raw movement detail.

This specific `activity` plus clipped `timelinePath` interpretation is an
inference from current reverse-engineered on-device exports and observed Google
Timeline UI behavior, not from an official Google JSON schema.

### Visit Normalization Direction

Recent on-device exports can emit multiple `visit` segments with the same
time window but different `hierarchyLevel` values for one stay.

For v1, the connector should import only one canonical visit event per exact
visit time window:

- prefer the lowest `hierarchyLevel`
- when the hierarchy level ties, prefer the candidate with the highest
  `topCandidate.probability`

This avoids duplicate canonical stay events for the same real-world visit while
still preserving the chosen hierarchy metadata in `raw_payload`.

### Canonical Mapping Direction

For the first increment, Google Maps Timeline segments should map into the
existing canonical event model as follows.

#### Visit Event Mapping

- segment `startTime` -> `Event.timestamp_start` in UTC
- segment `endTime` -> `Event.timestamp_end` in UTC
- `visit.topCandidate.placeLocation.latLng` -> `Event.latitude` /
  `Event.longitude`
- `Event.title`
  - use a normalized human-readable form of `semanticType` when available
  - otherwise fall back to `"Visit"`
- `Event.summary` remains empty in v1
- `raw_payload` stores only the selected semantic fields:
  - `segment_kind = "visit"`
  - `googlePlaceId`
  - `semanticType`
  - `visitProbability`
  - `candidateProbability`
  - `hierarchyLevel`
  - `isTimelessVisit` when present

#### Activity Event Mapping

- segment `startTime` -> `Event.timestamp_start` in UTC
- segment `endTime` -> `Event.timestamp_end` in UTC
- `activity.start.latLng` -> `Event.latitude` / `Event.longitude`
- `Event.title`
  - use a normalized human-readable form of `activity.topCandidate.type`
  - otherwise fall back to `"Movement"`
- `Event.summary` remains empty in v1
- `raw_payload` stores only the selected movement fields:
  - `segment_kind = "activity"`
  - `googleActivityType`
  - `activityProbability`
  - `topCandidateProbability`
  - `distanceMeters`
  - `startLocation`
  - `endLocation`
  - `pathPoints`

### Activity Path Reconciliation Direction

The connector should not assume that `timelinePath` and `activity` entries are
adjacent in array order.

Instead, it should:

1. parse all semantic segments with explicit start/end timestamps
2. collect all `timelinePath` segments separately
3. for each `activity` segment, gather every `timelinePath` segment whose time
   window overlaps that activity window
4. keep only path points whose timestamps fall within the activity window
5. prepend the `activity.start` point at the activity start timestamp
6. append the `activity.end` point at the activity end timestamp
7. sort the resulting points deterministically by timestamp and input order

`timelinePath` points outside the `activity` window must not be attached to that
activity event.

If no `timelinePath` points remain after clipping, the `activity` event should
still be created using only the activity boundary locations.

### Source Identity Direction

The new on-device export does not appear to expose a stable account or device
identifier inside the JSON payload.

For v1, canonical source identity should therefore be file-scoped and derived
from the resolved export path, for example:

- `google_maps_timeline:<resolved_export_path>`

The canonical source should store lightweight provenance in `config_json`, for
example:

- `origin_path`
- `export_format = "google_maps_timeline_on_device"`

### Idempotency Direction

One exported JSON document should correspond to one canonical source and one
full replacement set of canonical events.

The recommended idempotency model is source-scoped replacement with explicit
stable event identity:

- repeated import of the same file path must reuse the same canonical source
- each emitted event candidate must carry a deterministic `external_event_id`
- repeated import with unchanged semantic content must leave the database
  unchanged
- events previously persisted for that source but no longer present in the
  current JSON file must be counted as `missing_from_source` and deleted during
  the same ingest run

### Progress Direction

The connector should reuse the shared ingest progress architecture and expose at
least these lifecycle outcomes:

- `inserted`
- `updated`
- `unchanged`
- `failed`
- `missing_from_source`
- `persisted_event_count`

If unsupported or future semantic-segment kinds are skipped, the connector may
also expose a source-specific skipped-segment count in warnings or progress
payloads.

## Subtasks

- `R-038-01`
  - define Google Maps Timeline contracts and characterize the on-device
    fixture
- `R-038-02`
  - implement single-file JSON discovery and raw export loading boundaries
- `R-038-03`
  - transform semantic segments into canonical visit/activity candidates and
    reconcile activity paths
- `R-038-04`
  - persist the document-scoped source and canonical events through repository
    boundaries
- `R-038-05`
  - add missing-event reconciliation and delete sync for repeated imports of the
    same export file
- `R-038-06`
  - wire CLI entrypoints, progress reporting, and end-to-end tests

## Out of Scope

- no legacy Google Takeout `timelineObjects` import
- no `Records.json` import
- no `rawSignals` persistence
- no `userLocationProfile` persistence
- no `timelineMemory`, `trip`, or `note` ingestion yet
- no route geometry table or schema extension beyond existing event payload
  fields
- no attempt to merge multiple device exports into one logical source
- no source-specific daily-view or derive work in this series

## Acceptance Criteria

- a documented task series exists for the first `google_maps_timeline`
  connector
- the series explicitly targets the new on-device JSON format and rejects the
  older Google Takeout location-history formats
- the series explicitly states that `timelinePath` is not imported as a
  standalone canonical event type
- the series explicitly requires one canonical `timeline_activity` event per
  semantic `activity` segment with clipped path detail in `raw_payload`
- the series explicitly requires one canonical `timeline_visit` event per
  normalized visit time window
- the series explicitly requires file-scoped canonical source identity because
  the export lacks a stable intrinsic source id
- the series explicitly requires idempotent repeated import of the same file
  and delete synchronization for events removed from that file
- the series explicitly requires reuse of the staged ingest and shared progress
  architecture already established by the existing connectors

## Notes

The provided fixture at
`test/assets/googlemaps_timeline_test_fixture.json` is a good structural anchor
for the new format, but it should not be the only behavioral fixture.

The anonymized test file currently contains this concrete timestamp mismatch:

- the `timelinePath` segment window is on `2026-01-01`
- its individual `timelinePath[*].time` values are on `2025-03-25`

That means the checked-in fixture is suitable for field-shape characterization,
but not for executable assertions about path clipping into the `activity`
window. This series should therefore add at least one additional synthetic
fixture or inline test payload with aligned timestamps.

Research anchors used for this task proposal:

- Google Maps Help: `Manage your Google Maps Timeline`
  - https://support.google.com/maps/answer/6258979
  - confirms Timeline is now device-scoped, supports encrypted backups, and can
    be exported from the device
  - confirms Timeline shows visits and routes, including travel modes such as
    walking, cycling, driving, or public transport
- Qiita reverse-engineering article on the recent on-device JSON format
  - https://qiita.com/nabemax/items/3be12071d7ecd809aaa0
  - reverse-engineered field-level characterization of the recent on-device JSON
  - explicitly describes `activity`, `visit`, and `timelinePath` interaction
- Dawarich article `Building a Privacy-First Google Timeline Visualizer`
  - https://dawarich.app/blog/building-a-privacy-first-google-timeline-visualizer/
  - confirms current ecosystem handling of the new phone export format with
    `semanticSegments`
