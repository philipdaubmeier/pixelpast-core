# R-003 – CLI Skeleton

## Goal

Create a Typer-based CLI entrypoint for PixelPast.

This provides the operational interface for ingestion and derived jobs.

---

## Scope

Implement:

- `pixelpast ingest <source>`
- `pixelpast derive <job>`

CLI must:

- Load config (even if minimal stub)
- Initialize DB connection
- Print structured logging output
- Exit with proper status codes

Add entrypoint in `pyproject.toml`:

pixelpast = "pixelpast.cli.main:app"

---

## Out of Scope

- No real ingestion logic yet
- No real derive logic
- No scheduling
- No background workers

---

## Acceptance Criteria

- `pixelpast --help` works
- `pixelpast ingest photos` runs stub
- `pixelpast derive daily` runs stub
- DB connection initializes without errors

---

## Notes

Keep CLI thin.
No business logic inside CLI.
Only orchestration.