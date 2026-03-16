# R-034 - Workdays Vacation Direct-Color Grid

## Goal

Introduce a new `workdays_vacation` ingest source whose data can drive a
calendar-grid view where each day cell may carry its own direct color instead
of inheriting one shared view color with varying opacity.

This series should keep the existing architectural split intact:

- ingest writes canonical `Event` rows
- derive writes `DailyAggregate` rows
- the exploration API reads only derived grid data
- the UI consumes the API contract and does not recreate backend color logic

The intended user-visible outcome is a dedicated exploration view backed by an
Excel-based source where each imported day can expose:

- a direct day color
- an optional short label
- all-day event semantics represented through canonical events

## Dependencies

- `R-031-04`
- `R-033-02`
- `R-032`

## Scope

This series introduces a direct-color day-grid path alongside the existing
score-threshold intensity path.

### Canonical Direction

The new source should ingest spreadsheet rows into canonical `Event` records
instead of writing directly into derived tables.

Each spreadsheet row should represent one all-day timeline event for one day.
The canonical row should continue to use the existing `Event` schema, with the
day semantics represented through:

- `timestamp_start` at UTC midnight of the represented day
- `timestamp_end` at UTC midnight of the following day
- `Event.type = "workdays_vacation"`

The canonical payload may carry direct-color details and source-specific row
metadata in `raw_payload` and `derived_payload`.

### Derived Direction

The existing `daily_aggregate` model should be extended so one derived day row
can optionally carry:

- a nullable per-day `color_value`
- a nullable short `title`

For existing views those fields should remain `NULL`.

For the new workdays-vacation view, the selected derived rows should provide a
direct color from canonical source data instead of requiring score-threshold
resolution.

### Daily View Metadata Direction

The `daily_view` table should remain structurally unchanged.

The new view should instead be described through metadata conventions:

- `activity_score_color_thresholds = []`
- `direct_color = true`

That keeps the view catalog normalized while allowing one view to opt into
direct per-day color usage.

### API and UI Direction

The exploration grid contract should be simplified so per-day payloads carry
only the fields the UI actually needs.

The target day payload is:

- `date`
- `color`
- optional `label`

`color` should contain either:

- `empty`
- `low`
- `medium`
- `high`
- a direct hex color string beginning with `#`

If the corresponding `daily_aggregate.title` is `NULL`, the `label` field
should be omitted from the JSON payload entirely.

## Subtasks

- `R-034-01`
  - add the new `workdays_vacation` ingest skeleton and shared integration seams
- `R-034-02`
  - define spreadsheet parsing and canonical event transformation behavior
- `R-034-03`
  - extend `daily_aggregate` and ORM mappings with direct-color day fields
- `R-034-04`
  - update derive logic for workdays-vacation direct-color aggregate rows
- `R-034-05`
  - reshape the exploration grid API contract and adapt the UI to consume it

## Out of Scope

- no final spreadsheet fixture characterization in this series document
- no user-managed editing of imported day colors or labels
- no redesign of the broader day-detail API in this series
- no generalized arbitrary CSS color syntax beyond validated hex values
- no new `Event` schema columns solely for all-day support

## Acceptance Criteria

- a documented task series exists for a `workdays_vacation` ingest connector
- the series explicitly requires canonical event ingestion rather than direct
  derived writes
- the series explicitly requires nullable `daily_aggregate.color_value` and
  `daily_aggregate.title`
- the series explicitly states that the workdays-vacation `DailyView` remains
  metadata-driven, with empty score thresholds and `direct_color = true`
- the series explicitly changes the exploration grid day payload to
  `date` / `color` / optional `label`
- the series explicitly requires the UI to recognize direct hex colors without
  an additional `color_mode` field

## Notes

This series deliberately keeps the direct-color behavior narrow.

The key design choice is:

- canonical source data stays canonical as `Event`
- derive remains the only writer of `DailyAggregate`
- direct colors are modeled as a view-specific derived behavior, not as a
  global replacement for the existing intensity-based views
- populated workbook cells whose short code cannot be resolved through the
  legend are skipped during ingest and therefore never reach derive
