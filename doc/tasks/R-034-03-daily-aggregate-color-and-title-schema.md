# R-034-03 - Daily Aggregate Color and Title Schema

## Goal

Extend the derived schema so one `daily_aggregate` row can optionally carry a
direct per-day color and a short label.

This task is the schema and ORM foundation for the workdays-vacation direct
color view.

## Dependencies

- `R-034`

## Scope

### Schema Direction

Add the following nullable columns to `daily_aggregate`:

- `color_value`
- `title`

`color_value` should be nullable so existing views can continue to rely on
score-threshold color resolution without storing a per-day direct color in the
row itself.

`title` should be a nullable short text field with a maximum length of 255
characters.

### ORM Direction

Update the SQLAlchemy mapping and related repository snapshot shapes so these
new fields exist throughout the derived persistence layer.

The repository and persistence code should remain explicit about these fields
being optional and day-varying.

### Migration Direction

Add a dedicated Alembic migration for the schema extension.

The migration should preserve all existing data and backfill the new columns as
`NULL` for preexisting rows.

### Behavioral Direction

After this task:

- existing views still work with `NULL` `daily_aggregate.color_value`
- existing views still work with `NULL` `daily_aggregate.title`
- no direct-color behavior is activated yet purely by the schema change

## Out of Scope

- no derive logic changes yet
- no API contract changes yet
- no UI changes yet
- no structural changes to `daily_view`

## Acceptance Criteria

- `daily_aggregate` has nullable `color_value` and nullable `title`
- the ORM model exposes both fields cleanly
- repository snapshot/persistence types can carry both values
- the migration preserves existing rows with `NULL` backfill
- tests cover the updated schema and ORM round-trip behavior

## Notes

This task intentionally does not decide how `color_value` is interpreted by the
grid API. It only introduces storage for optional day-specific derived color
and label data.
