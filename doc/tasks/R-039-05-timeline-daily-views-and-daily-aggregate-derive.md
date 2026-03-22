# R-039-05 - Timeline Daily Views and Daily Aggregate Derive

## Goal

Extend the daily aggregate derive job so canonical timeline movement data becomes
visible through two new generic derived daily views:

- one view for `timeline_visit`
- one view for `timeline_activity`

The important boundary for this task is:

- the derived views must stay generic and must not mention Google Maps or any
  other concrete provider in their persisted identity
- the derive behavior should consume canonical event types and derived
  place-link state, not provider-specific raw-source naming
- the existing `daily_view` and `daily_aggregate` schema should remain
  structurally unchanged

## Dependencies

- `R-031-03`
- `R-038-03`
- `R-039-04`

## Scope

### Introduce Two Generic Timeline Daily Views

Keep the `daily_view` schema unchanged, but add two deterministic derived view
identities for timeline exploration:

- one for visit activity derived from canonical `Event.type = "timeline_visit"`
- one for movement activity derived from canonical `Event.type = "timeline_activity"`

For this task, the persisted view identity should remain generic and canonical,
for example through:

- `aggregate_scope = "source_type"`
- `source_type = "timeline_visit"`
- `source_type = "timeline_activity"`

Do not introduce provider-branded identities such as `google_maps`,
`google_maps_timeline`, or similar in `daily_view`.

### Keep Timeline Views Independent from Provider Branding

The derive selection rule must be based on canonical event typing, not on the
connector that originally produced the event.

This means:

- `timeline_visit` rows are selected by `Event.type = "timeline_visit"`
- `timeline_activity` rows are selected by `Event.type = "timeline_activity"`
- the new derived views must not be partitioned by `Source.type = "google_maps_timeline"`

The resulting views are timeline-mode projections, not import-source views.

### Add a Visit-Oriented Daily Aggregate View

The daily aggregate builder should produce one additional row per day for the
generic timeline-visit view when qualifying events exist.

For this view:

- `total_events` is the number of canonical `timeline_visit` events on that day
- `media_count` remains zero unless the existing generic builder semantics
  explicitly require otherwise
- `activity_score` should continue to follow the regular score contract unless a
  dedicated score override is already supported elsewhere

### Build Visit Location Summaries from Derived Place Links

For the timeline-visit view, `location_summary` should represent visit places at
day granularity using reusable derived place records where available.

At minimum, each location summary item should contain:

- latitude
- longitude
- display label taken from `place.display_name`

Behavior expectations:

- multiple visits to the same resolved place on one day should aggregate
  deterministically
- visits should use the derived `event_place -> place` relationship rather than
  provider-specific raw payload fields
- unresolved visits may still contribute to `total_events`, but this task should
  not require a provider-specific fallback naming path

### Add an Activity-Oriented Daily Aggregate View

The daily aggregate builder should also produce one additional row per day for
the generic timeline-activity view when qualifying events exist.

For this view:

- `activity_score` is the total distance traveled on that day in kilometers
- the distance source should come from canonical `timeline_activity` event data,
  using the existing canonical payload field that stores the segment distance
- all movement modes for the day should contribute to the same daily row

This row is intentionally movement-oriented rather than count-oriented.

### Build an Activity Title from the Top Three Movement Modes

For the timeline-activity view, `title` should summarize the three most
significant movement modes of the day by aggregated traveled distance.

The intended direction is:

- group the day by canonical movement title or activity label
- sum the distance per movement mode
- sort deterministically by descending distance, then by normalized label
- render the top three groups into a compact summary such as
  `"23 km Bicycle, 12 km Walking, 2 km Car"`

Formatting should stay backend-owned and deterministic.

### Build an Activity Location Summary from Path Points

For the timeline-activity view, `location_summary` should include the activity
waypoints of the day as raw map points.

At minimum, each item should contain:

- latitude
- longitude

This task should explicitly exclude:

- timestamps in the location summary payload
- labels or titles on individual activity waypoints

The derive path may consume canonical `raw_payload.pathPoints` as produced by
the current timeline-activity ingestion flow, but it should do so as canonical
timeline activity data rather than as provider-branded logic.

### Extend Daily View Metadata Deterministically

The new timeline visit and timeline activity views should persist human-readable
`daily_view` metadata through the existing metadata path.

The labels and descriptions should remain generic, for example aligned with:

- "Timeline Visits"
- "Timeline Activity"

Do not introduce provider-branded labels in persisted daily-view metadata.

### Preserve Existing Overall Daily Aggregate Behavior

This task should add the two new timeline-specific views without removing or
changing the existing overall daily aggregate rows.

Existing canonical events may therefore contribute to:

- the overall daily view
- their existing source-scoped daily views where already defined
- the new generic timeline visit or timeline activity views described here

### Add Focused Test Coverage

Add automated coverage that confirms at least:

- derive persists or reuses a `daily_view` for `timeline_visit`
- derive persists or reuses a `daily_view` for `timeline_activity`
- `timeline_visit` events generate visit-view daily aggregate rows
- `timeline_activity` events generate activity-view daily aggregate rows
- visit-view `total_events` equals the count of visit events for the day
- visit-view `location_summary` uses derived place display names and coordinates
- activity-view `activity_score` equals total traveled kilometers for the day
- activity-view `title` renders the top three movement modes by aggregated
  distance
- activity-view `location_summary` contains only coordinate points without
  labels or timestamps
- no provider-branded `daily_view` identity such as `google_maps_timeline` is
  introduced by this task

## Out of Scope

- no schema changes to `daily_view` or `daily_aggregate`
- no UI changes
- no provider-specific view identity such as `google_maps_timeline`
- no change to canonical event typing or ingest behavior
- no new map-specific API endpoints
- no reverse-geocoding fallback for unresolved visits

## Acceptance Criteria

- derive persists or reuses two new generic timeline daily views for
  `timeline_visit` and `timeline_activity`
- the new views are not provider-branded
- visit-view rows count daily `timeline_visit` events through `total_events`
- visit-view rows expose place-based `location_summary` items using coordinates
  and display names from derived place records
- activity-view rows aggregate traveled distance into `activity_score` in
  kilometers
- activity-view rows render a deterministic top-three movement-mode `title`
- activity-view rows expose waypoint-only `location_summary` items without
  labels or timestamps
- tests explicitly cover both new views and confirm provider branding is absent

## Notes

This task intentionally treats timeline visit and timeline movement projections
as generic chronology views layered on top of canonical events and derived place
links.

That keeps the derived exploration model aligned with the canonical domain
rather than with one specific import provider.
