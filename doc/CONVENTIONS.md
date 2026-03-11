# PixelPast – Conventions

## Architectural Rules

- Strict Raw → Canonical → Derived separation
- No direct DB access outside service layer
- Connectors must not contain business logic

## Code Style

- Python 3.12+
- Mandatory type annotations
- Ruff for linting and formatting (Black formatting style)
- Pydantic for DTOs (Data Transfer Objects)
- SQLAlchemy 2.x ORM
- Alembic for migrations

## Testing

- pytest required
- Ingestion must be idempotent
- Tests must cover:
  - Repeated execution
  - Empty sources
  - Error handling
  - Partial failures

## CLI

Typer-based command structure:

    pixelpast ingest <source>
    pixelpast derive <job>

## Database Conventions

- All timestamps stored in UTC
- Location coordinates stored as nullable WGS84 decimal degree values (`latitude`, `longitude`) using `REAL` columns. This keeps ingestion simple and supports efficient bounding-box queries, e.g. 48.137285, 11.575478
- JSON fields allowed for extensibility
- No denormalization without justification
- Indexes required for:
  - timestamp_start
  - source_id
  - event.type

## Commits

- Small, focused changes
- Separate migrations per schema change
- No scope creep within a task

## Design Philosophy

Explorability over perfect normalization.
Clarity over cleverness.
Determinism over magic.