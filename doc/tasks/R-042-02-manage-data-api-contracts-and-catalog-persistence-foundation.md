# R-042-02 - Manage Data API Contracts and Catalog Persistence Foundation

## Goal

Introduce the backend read and write contracts needed by the `Manage Data`
workspace for canonical `Person` and `PersonGroup` catalog maintenance.

This task should establish explicit service, repository, and REST boundaries
for manage-data mutations instead of leaking ORM logic into the UI-facing
layer.

## Dependencies

- `R-003`
- `R-037`

## Scope

### Introduce a Dedicated Manage-Data Route Family

Add explicit REST endpoints for manage-data catalog loading and batch saving.

The first route family should cover:

- persons catalog load
- persons catalog batch save
- person-groups catalog load
- person-groups catalog batch save

Membership-specific routes may remain for `R-042-05`.

The contracts should be read-oriented and explicit.
Do not expose ORM models directly.

### Add Manage-Data Schemas

Introduce API schemas for the new catalog surfaces.

The person contract should expose:

- identifier
- display name
- aliases as `string[]`
- path

The person-group contract should expose:

- identifier
- display name
- read-only member count

Server-owned fields that are not currently editable in the UI should stay out
of the public schema unless needed for correctness.

### Add Catalog Persistence Services and Repositories

Create explicit persistence-facing services or repositories for manual catalog
editing.

Required behavior:

- list persons deterministically
- batch create or update persons
- reject person deletions in the v1 write contract
- list person groups deterministically
- batch create, update, and delete person groups
- surface member counts for the group catalog

Do not overload ingest-oriented repositories with UI-specific write semantics
if that would blur responsibilities.

### Define Validation and Server-Owned Defaults

The backend contract must define the first manage-data validation rules.

Required rules:

- person `path` must remain unique when present
- aliases must persist as a normalized string-list shape, not arbitrary JSON
- person-group writes own `type` server-side as a fixed manual-management value
- deleting a group must remove only the group and its membership links

### Keep Section Loading Explicit

These endpoints are section-scoped by design.

Do not introduce one large manage-data bootstrap endpoint in this task.
Each section should be loaded independently when the UI enters it.

## Out of Scope

- no person-group membership editing endpoints
- no person deletion support
- no merge or dedupe logic
- no search endpoint or pagination contract
- no authentication or permission model

## Acceptance Criteria

- dedicated manage-data REST contracts exist for persons and person-group
  catalogs
- API request and response bodies use explicit schemas rather than ORM models
- the persons write path supports create and update but rejects delete semantics
- the person-groups write path supports create, update, and delete
- person `path` uniqueness is validated server-side
- aliases persist through an explicit string-list contract
- person-group `type` is assigned server-side for manually managed groups
- section data can be fetched independently without a global manage-data
  bootstrap payload
- API documented with examples like the other APIs

## Notes

This task should create the backend contract boundary that the UI tasks can
target without baking persistence assumptions into the frontend.
