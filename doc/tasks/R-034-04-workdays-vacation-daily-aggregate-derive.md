# R-034-04 - Workdays Vacation Daily Aggregate Derive

## Goal

Extend the daily-aggregate derive path so the new `workdays_vacation` canonical
events produce a direct-color derived view.

This task is where the new schema becomes behaviorally meaningful.

## Dependencies

- `R-034-02`
- `R-034-03`
- `R-034`

## Scope

### Daily View Metadata Direction

Keep the `daily_view` table unchanged, but ensure the workdays-vacation view is
persisted with metadata that explicitly opts out of score-threshold mapping and
opts into direct-color semantics.

The intended metadata additions for that view are:

```json
{
  "activity_score_color_thresholds": [],
  "direct_color": true
}
```

This should coexist with the existing metadata structure rather than replacing
it wholesale.

### Derive Input Direction

Extend the derive loading and builder flow so it can recognize canonical events
with:

- `Event.type = "workdays_vacation"`

The derive path should load enough canonical event data to extract:

- the represented UTC day
- the imported direct color value
- the imported short title

Because `R-034-02` now defines legend misses as skipped ingest rows, derive may
assume that only legend-resolved canonical `workdays_vacation` events reach
this stage.

### Special-Case Aggregate Direction

The daily aggregate builder should add a dedicated branch for
`workdays_vacation` events.

For the corresponding direct-color view:

- `daily_aggregate.color_value` should be populated from the imported canonical
  event payload
- `daily_aggregate.title` should be populated from the imported canonical title
  or equivalent preserved label field
- the derived row should represent the all-day event on its intended day

Existing non-workdays views should continue to leave `daily_aggregate.color_value`
and `daily_aggregate.title` as `NULL`.

Skipped legend-miss cells from ingest must not result in derived aggregate rows.

### Compatibility Direction

The new direct-color behavior must not break the existing score-based views.

For traditional views, the derive and read behavior should continue to work as
before:

- thresholds in `daily_view.metadata` still determine color token resolution
- no direct color is stored on the aggregate row

### Determinism Direction

If the spreadsheet source can produce more than one workdays-vacation event for
the same UTC day, the derive path must apply one explicit and documented rule
for conflict resolution instead of silently accepting unstable results.

The exact rule may depend on the fixture characterization, but it must be
deterministic and covered by tests.

## Out of Scope

- no exploration API contract changes yet
- no UI changes yet
- no redesign of the generic activity-score formula
- no generalized custom per-day styling framework beyond this source-specific
  derived behavior

## Acceptance Criteria

- the derive path recognizes canonical `workdays_vacation` events
- a dedicated daily view is persisted with empty score thresholds and
  `direct_color = true`
- matching derived rows write `daily_aggregate.color_value`
- matching derived rows write `daily_aggregate.title`
- existing score-based views keep functioning with `NULL` direct-color fields
- legend-miss cells skipped during ingest do not create direct-color derived
  rows
- tests cover the direct-color row generation and any same-day conflict rule

## Notes

The important boundary here is that the special case belongs in derive, not in
ingest and not in the UI.

The UI should receive an already-decided per-day color, while canonical ingest
remains a faithful import of source facts.
