# R-037 - OpenAPI Documentation Foundation

## Goal

Introduce a consistent OpenAPI documentation workflow for the PixelPast API so
all public endpoints are documented through one exported contract and concrete
examples become part of the maintained backend surface.

## Dependencies

- `R-035-03`
- `R-036-06`

## Scope

### Documentation Policy

Establish one repository-wide API documentation convention:

- FastAPI route and schema metadata remain the source of truth
- the exported contract lives at `doc/api/openapi.yaml`
- generated HTML is not checked into Git by default
- renderer configuration or generation scripts are checked in once introduced

### Contract Coverage

Ensure every public backend endpoint under `src/pixelpast/api/routes/` is
represented in the exported OpenAPI contract with explicit metadata.

Current endpoint surface includes:

- `GET /api/health`
- `GET /api/exploration/bootstrap`
- `GET /api/exploration`
- `GET /api/days/context`
- `GET /api/days/{day}`
- `GET /api/social/graph`

### Example Coverage

The OpenAPI contract should contain concrete examples for:

- representative success responses
- important query combinations
- important validation or boundary failures where the endpoint contract is
  expected to return a deterministic error response

Examples should be realistic for PixelPast's chronology-centered exploration
domain rather than placeholder values.

### Rendering Direction

Provide a minimal path for both:

- local developer inspection through FastAPI's built-in docs
- static HTML generation from the committed OpenAPI contract for sharing or CI
  publishing

### Validation Direction

The project should gain a simple repeatable way to verify that:

- the OpenAPI export can be regenerated deterministically
- the exported contract stays in sync with the live FastAPI application
- obvious contract regressions can be caught in review or CI

## Out of Scope

- no broader developer portal or multi-product docs platform
- no GraphQL documentation
- no versioned public API lifecycle policy yet
- no implementation of client SDK generation unless a concrete consumer appears

## Acceptance Criteria

- `doc/api/` becomes the documented home for committed API contract artifacts
- `doc/api/openapi.yaml` is defined as the canonical exported contract location
- every current public endpoint appears in the exported OpenAPI schema
- every current public endpoint has meaningful summaries or descriptions
- representative success examples are included for all public endpoints
- intended validation or boundary error responses are documented where
  applicable
- the repository includes a documented rendering path for static HTML output
- the repository includes a documented or automated sync-check path for the
  exported contract

## Notes

This task is intentionally documentation-foundation first. The important
boundary is that contract metadata should stay close to the FastAPI
implementation while the exported OpenAPI file becomes the reviewable published
artifact.
