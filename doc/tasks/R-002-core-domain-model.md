# R-002 – Core Domain Model (Event, Asset, Source, ImportRun, Tag, Person)

## Goal

Implement the minimal canonical domain model as defined in DOMAIN_MODEL.md.

This establishes the core database schema and ORM mappings.

---

## Scope

Implement SQLAlchemy 2.x models for:

- Source
- ImportRun
- Event
- Asset
- Tag
- EventTag
- Person
- EventPerson
- EventAsset

Include:

- Proper relationships
- UTC timestamps
- JSON columns where specified
- `latitude` and `longitude` as REAL
- Appropriate nullable constraints

Add:

- Alembic setup
- Initial migration

---

## Out of Scope

- No ingestion logic
- No CLI
- No API routes
- No seed data

---

## Acceptance Criteria

- Database can be created
- Migration runs successfully
- Tables match DOMAIN_MODEL.md
- Indexes:
  - Event.timestamp_start
  - Event.type
  - Asset.timestamp
- Coordinates stored as REAL
- All timestamps UTC

---

## Notes

Do not over-model.
No extra tables.
No premature optimization.
No Location entity.