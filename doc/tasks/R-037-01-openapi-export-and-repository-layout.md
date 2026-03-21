# R-037-01 - OpenAPI Export and Repository Layout

## Goal

Create the minimal repository structure and workflow needed to publish the
backend OpenAPI contract as a checked-in artifact.

## Dependencies

- `R-037`

## Scope

- create the `doc/api/` documentation home
- define `doc/api/openapi.yaml` as the canonical exported contract path
- add a short `doc/api/README.md` describing source of truth, export workflow,
  and HTML rendering direction
- add the minimal script or command path needed to export the FastAPI OpenAPI
  schema deterministically

## Acceptance Criteria

- `doc/api/` is documented as the canonical API documentation location
- the repository has a deterministic contract export path
- the exported contract file location is stable and review-friendly
- generated HTML is explicitly excluded from the default checked-in artifacts
