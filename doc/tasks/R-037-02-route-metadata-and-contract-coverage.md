# R-037-02 - Route Metadata and Contract Coverage

## Goal

Bring all current public endpoints up to a consistent OpenAPI metadata quality
bar.

## Dependencies

- `R-037-01`

## Scope

Add or refine route-level OpenAPI metadata for:

- `GET /api/health`
- `GET /api/exploration/bootstrap`
- `GET /api/exploration`
- `GET /api/days/context`
- `GET /api/days/{day}`
- `GET /api/social/graph`

This should include, where applicable:

- summaries and descriptions
- stable tags
- parameter descriptions
- validation constraints
- explicit response descriptions
- documented contract-level error responses

## Acceptance Criteria

- every current public endpoint has meaningful OpenAPI metadata
- parameter semantics are understandable from the schema without reading code
- expected validation errors are documented where they are part of the intended
  contract
- the exported schema reads as a usable external contract, not only framework
  output
