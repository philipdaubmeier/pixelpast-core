# R-004 - CLI Skeleton

## Goal

Create the Typer-based operational entrypoint for ingestion and derived jobs.

This task provides the command surface that later workers and jobs will use.

---

## Scope

Implement:

- `pixelpast ingest <source>`
- `pixelpast derive <job>`

CLI behavior must include:

- settings initialization
- database initialization
- structured logging output
- explicit exit codes
- thin orchestration only

Add the console entrypoint in `pyproject.toml`.

---

## Out of Scope

- No real connector execution yet
- No real derive job behavior yet
- No scheduler
- No worker daemon

---

## Acceptance Criteria

- `pixelpast --help` works
- `pixelpast ingest photos` runs a stub command successfully
- `pixelpast derive daily-aggregate` runs a stub command successfully
- CLI wiring reuses shared app and persistence foundation

---

## Notes

Keep business logic out of the CLI layer.
The CLI should call services or job entrypoints, not implement them.
