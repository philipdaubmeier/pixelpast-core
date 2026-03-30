# R-043-01 - Asset Short ID Schema and Backfill

## Goal

Extend the canonical asset schema with a stable public short id and backfill it
for every existing asset row.

This task establishes the identifier used by all later thumbnail and original
media routes.

## Dependencies

- `R-043`

## Scope

### Add A Canonical `Asset.short_id`

Introduce a new canonical asset column:

- name: `short_id`
- required: yes
- uniqueness: global across all assets
- length: fixed at 8 characters
- alphabet: Base58 without `0`, `O`, `I`, or `l`

The schema change should include the database-level uniqueness guarantee needed
for public media identifiers.

### Backfill Existing Assets

The migration must populate `short_id` for all existing asset rows.

The backfill contract should be:

- start from the existing persisted asset primary key as the stable seed input
- generate an 8-character Base58 identifier
- if a collision occurs, retry with additional generated candidates until a
  unique value is found
- write the final unique value back into the row during migration

The migration must leave the repository with no canonical asset row lacking a
`short_id`.

### Update ORM And Repository Contracts

The ORM mapping and write repository interfaces should be updated so
`short_id` becomes part of the canonical asset persistence model.

Required outcomes:

- ORM `Asset` exposes the new column
- repository read and write types understand the field
- asset upsert logic can preserve an existing short id

Do not change the meaning of `external_id`.

### Preserve Existing Asset Identity Rules

This task must not redesign canonical asset identity.

Required constraints:

- `external_id` remains the connector-scoped ingest identity
- `(source_id, external_id)` uniqueness remains intact
- `short_id` is an additional public delivery key, not a replacement for
  ingest identity

## Out of Scope

- no thumbnail generation
- no media API routes
- no connector-specific storage-root validation beyond what is needed to add
  the new schema field

## Acceptance Criteria

- the canonical `asset` table contains a non-null `short_id` column
- the database enforces global `short_id` uniqueness
- the migration backfills `short_id` for all existing assets
- ORM and repository contracts expose `short_id`
- existing `external_id` semantics remain unchanged

## Notes

This task should keep the implementation boundary narrow: schema and identity
foundation first, no delivery behavior yet.
