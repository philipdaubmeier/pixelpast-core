# R-003 - Canonical Schema v0

## Goal

Implement the first coherent canonical schema for PixelPast based on
`doc/DOMAIN_MODEL.md`.

This task establishes the relational core used by ingestion, analytics and API
projection layers.

---

## Scope

Implement SQLAlchemy 2.x mappings and an initial migration for:

- `Source`
- `ImportRun`
- `Event`
- `Asset`
- `EventAsset`
- `Tag`
- `EventTag`
- `AssetTag`
- `Person`
- `EventPerson`
- `AssetPerson`
- `PersonGroup`
- `PersonGroupMember`

Include:

- primary keys and foreign keys
- nullable constraints matching the documented model
- JSON columns where specified
- UTC timestamp handling
- indexes for:
  - `Event.timestamp_start`
  - `Event.source_id`
  - `Event.type`
  - `Asset.timestamp`

---

## Out of Scope

- No repositories beyond what is required for migration/runtime wiring
- No ingestion logic
- No analytics jobs
- No API read models
- No seed data

---

## Acceptance Criteria

- migration runs successfully on SQLite
- schema matches the intended v0 canonical model
- all core association tables are present
- timestamps are stored in UTC
- schema supports both `Event` and `Asset` as first-class temporal entities

---

## Notes

Do not collapse `Asset` into `Event`.
Do not add speculative entities outside the documented canonical model.
