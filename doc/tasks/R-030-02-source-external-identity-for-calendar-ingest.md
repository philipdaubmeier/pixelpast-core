# R-030-02 - Source External Identity for Calendar Ingest

## Goal

Extend canonical source persistence so calendar documents can be matched and
reused through a stable calendar-level external identifier.

The current `Source` model only supports uniqueness by `(type, name)`. That is
not sufficient for calendar ingest because exported calendar names can change,
while the calendar-level identifier should remain the stable identity key.

## Dependencies

- `R-030-01`

## Scope

### Add `Source.external_id`

Extend the canonical source model, repository layer, and migration chain with a
new `external_id` field on `Source`.

The field should be:

- nullable for existing non-calendar sources
- unique when present
- available in both ORM and repository code

This is the only intended canonical schema extension for the calendar ingest
increment.

### Add Repository Support for External Source Identity

Extend `SourceRepository` so later calendar tasks can:

- look up a source by `external_id`
- create or update a source by `external_id`
- continue to support the current photo-source behavior without regression

The repository API should stay explicit rather than overloading unrelated
methods with ambiguous optional arguments.

### Define Calendar Source Config Semantics

Document how `Source.config` should represent the calendar document origin.

For direct `.ics` files:

- store the absolute file path

For `.ics` files originating from a zip archive:

- store the absolute archive path
- store the member path inside the archive

Do not pretend a zip member has an extracted on-disk absolute path when no such
file exists.

### Preserve Existing Behavior for Photos

The photo ingest path currently creates or updates one synthetic `photos`
source. That behavior should remain valid after `Source.external_id` is added.

## Out of Scope

- no calendar event parsing yet
- no CLI ingest wiring yet
- no event persistence yet

## Acceptance Criteria

- `Source` has a new `external_id` field in the ORM model and database schema
- an Alembic migration is planned for the schema change
- uniqueness is enforced for non-null `external_id` values
- repository methods exist to find and reconcile sources by external identity
- existing photo-source persistence behavior remains supported without forcing an
  external identifier onto that connector
- the expected `Source.config` shape for direct files and zip members is stated
  explicitly in the task outcome

## Notes

Calendar ingest should use the actual calendar-level identifier header observed
in the parsed document, not a filesystem path, as the long-lived source
identity.
