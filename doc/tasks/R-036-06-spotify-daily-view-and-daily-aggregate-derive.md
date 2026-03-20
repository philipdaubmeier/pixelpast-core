# R-036-06 - Spotify Daily View and Daily Aggregate Derive

## Goal

Extend the daily-view metadata and daily-aggregate derive path so canonical
Spotify imports produce a dedicated Spotify source-scoped exploration view.

This task makes the new connector visible in the derived exploration model.

## Dependencies

- `R-031-03`
- `R-036-04`

## Scope

### Daily View Metadata Direction

Keep the `daily_view` schema unchanged, but ensure Spotify activity resolves to
its own persisted source-scoped view metadata.

The intended identity is:

- `aggregate_scope = "source_type"`
- `source_type = "spotify"`

This view should use the regular score-based metadata path rather than direct
color semantics.

### Derive Input Direction

Ensure the derive loading and builder flow treats canonical Spotify events as
Spotify source activity through the existing source-type partitioning model.

This task should make explicit that:

- canonical `Event.type = "music_play"` does not become the derived
  `daily_view.source_type`
- the source-scoped derived view identity comes from canonical
  `Source.type = "spotify"`
- Spotify events still contribute to the overall activity view

### Daily Aggregate Behavior Direction

For v1, Spotify activity should use the standard event-count contribution path:

- each canonical Spotify event contributes to `total_events`
- Spotify rows participate in the regular activity-score formula
- no Spotify-specific direct-color or title override behavior is introduced

### Metadata Direction

Add deterministic backend-owned metadata for the Spotify view so existing read
surfaces can render it without special casing.

The label and description should be explicit and human-readable, for example
aligned with "Spotify" rather than the internal event type `music_play`.

### Test Coverage Direction

Add automated coverage that confirms:

- derive persists or reuses a `daily_view` row for `source_type = "spotify"`
- Spotify canonical events generate Spotify source-scoped aggregate rows
- Spotify canonical events also generate overall aggregate rows
- no accidental `daily_view` is created for `source_type = "music_play"`

## Out of Scope

- no schema changes to `daily_view` or `daily_aggregate`
- no UI changes
- no Spotify-specific activity-score formula redesign

## Acceptance Criteria

- derive persists or reuses a Spotify `daily_view`
- the Spotify `daily_view` uses `source_type = "spotify"`
- Spotify events contribute to both overall and Spotify source-scoped rows
- Spotify uses the existing score-based derive path without direct-color
  special cases
- tests explicitly confirm that `music_play` remains the canonical event type
  while `spotify` remains the derived source-scoped view identity

## Notes

This task is intentionally derived-layer only. The important boundary is that
canonical event typing and derived source partitioning remain distinct and
explicit.
