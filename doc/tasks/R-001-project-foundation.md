# R-001 - Project Foundation

## Goal

Create the initial PixelPast repository structure and baseline tooling in a way
that matches the intended architecture from the start.

This task establishes the minimal foundation for all later work without
introducing product logic.

---

## Scope

Create and configure:

- Python package root and explicit package boundaries:
  - `pixelpast/domain/`
  - `pixelpast/persistence/`
  - `pixelpast/api/`
  - `pixelpast/ingestion/`
  - `pixelpast/analytics/`
  - `pixelpast/cli/`
  - `pixelpast/shared/`
- `pyproject.toml`
- editable install support
- Ruff configuration
- pytest configuration
- `.gitignore`
- package `__init__.py` files only where needed

Document the intended package roles briefly in repository-facing docs if they
do not already exist.

---

## Out of Scope

- No database models yet
- No FastAPI app yet
- No CLI commands yet
- No ingestion logic
- No analytics logic

---

## Acceptance Criteria

- `pip install -e .` works
- `ruff check .` runs without errors
- `pytest` runs successfully
- package structure reflects architectural boundaries from `AGENTS.md`
- no placeholder junk files or ambiguous top-level `models/` package

---

## Notes

Keep the structure minimal and explicit.
Do not introduce generic helper buckets unless they are clearly justified.
