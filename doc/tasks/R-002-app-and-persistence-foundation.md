# R-002 - App and Persistence Foundation

## Goal

Establish the shared runtime foundation for the API, CLI, ingestion jobs and
analytics jobs.

This task creates the application bootstrap layer before feature-specific code
is added.

---

## Scope

Implement:

- settings loading for local development
- database engine and session factory
- persistence base setup for SQLAlchemy 2.x
- Alembic configuration and migration environment
- minimal FastAPI app factory
- router registration pattern
- dependency injection for database sessions

Provide a minimal health-style route such as:

- `GET /health`

---

## Out of Scope

- No canonical tables yet
- No timeline endpoints yet
- No ingestion connectors yet
- No scheduling
- No business logic

---

## Acceptance Criteria

- FastAPI app starts successfully
- Alembic environment is initialized and usable
- database session can be created from both API and non-API code
- API route registration is in place
- no ORM models are leaked through the API layer

---

## Notes

Keep the app factory thin.
This task is about wiring and boundaries, not feature behavior.
