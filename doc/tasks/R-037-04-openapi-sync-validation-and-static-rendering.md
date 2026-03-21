# R-037-04 - OpenAPI Sync Validation and Static Rendering

## Goal

Add a lightweight validation and rendering workflow around the committed OpenAPI
contract.

## Dependencies

- `R-037-03`

## Scope

- add a repeatable contract sync check between the FastAPI app and
  `doc/api/openapi.yaml`
- define or implement a minimal static HTML rendering path from the committed
  contract
- document how local developers and CI can regenerate the contract and the HTML
  output

The initial rendering path should stay simple and avoid introducing a large
documentation platform.

## Acceptance Criteria

- the repository can verify whether the committed OpenAPI file is stale
- the OpenAPI contract can be rendered to static HTML from the committed source
- the workflow is documented clearly enough for local use and CI adoption
- the static HTML artifact remains generated output rather than a default
  checked-in file
