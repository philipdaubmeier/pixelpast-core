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

## API Documentation

OpenAPI documentation must follow one repository-wide convention.

### Source of Truth

- The FastAPI application is the primary source of truth for the live OpenAPI schema.
- Route metadata, request/response schemas, examples, tags, summaries, and error responses must be defined close to the API implementation in `src/pixelpast/api/`.
- A generated OpenAPI export is the published contract artifact for review and external consumption.

### Location

- Store API documentation artifacts under `doc/api/`.
- The canonical exported contract file should be `doc/api/openapi.yaml`.
- Keep a short human-written overview in `doc/api/README.md`.
- Optional request/response example payloads may live under `doc/api/examples/` when they become large enough to justify separate files.

Avoid alternative folder names such as `doc/apidoc` unless there is a strong migration reason.

### Git Policy

- Check in the raw OpenAPI contract file.
- Check in renderer configuration, custom templates, or generation scripts when introduced.
- Do not check in generated HTML documentation by default.
- Generated static HTML may be produced locally or in CI for publishing, previews, or releases.

### Rendering Policy

- FastAPI built-in docs are acceptable for local development and quick inspection.
- Static HTML output should be generated from the committed OpenAPI contract, not maintained manually.
- Prefer a simple renderer setup such as Swagger UI or ReDoc before introducing a larger documentation toolchain.

### Coverage Expectations

- Every public endpoint must appear in the OpenAPI schema.
- Every endpoint must have a clear summary or description.
- Every endpoint must declare explicit response models where appropriate.
- Non-trivial query parameters and path parameters must include descriptions and constraints.
- Error responses that are part of the intended contract must be documented explicitly.
- Concrete examples should be provided for representative success payloads and important validation or boundary cases.

### Change Management

- API-facing changes should update the OpenAPI contract in the same change set.
- API reviews should treat the exported OpenAPI file as a contract diff, not only an implementation detail.
- If generated docs and runtime behavior diverge, fix the implementation metadata first and then re-export the contract.

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
