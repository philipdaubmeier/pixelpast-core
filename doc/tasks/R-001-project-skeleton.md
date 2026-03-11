# R-001 – Project Skeleton & Tooling Foundation

## Goal

Create the initial PixelPast project structure with minimal but production-ready
tooling and configuration.

This task establishes the technical foundation for all further development.

---

## Scope

- Create Python package structure:
  - `pixelpast/`
  - `pixelpast/api/`
  - `pixelpast/db/`
  - `pixelpast/ingestion/`
  - `pixelpast/cli/`
- Add `pyproject.toml`
- Configure:
  - Python 3.12+
  - Ruff (lint + format)
  - pytest
- Create empty `__init__.py` files
- Add minimal README placeholder if missing
- Add `.gitignore`
- Ensure project installs in editable mode

---

## Out of Scope

- No database models yet
- No API implementation
- No business logic
- No ingestion logic

---

## Acceptance Criteria

- `pip install -e .` works
- Ruff runs without errors
- `pytest` runs (even if no tests yet)
- Clean directory structure exists
- No unused or placeholder junk files

---

## Notes

Keep structure minimal.
Do not introduce premature abstractions.
Do not add dependencies not strictly required.