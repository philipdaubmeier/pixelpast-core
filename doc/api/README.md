# API Documentation

`doc/api/` is the canonical home for checked-in PixelPast API contract artifacts.

## Source Of Truth

The primary source of truth is the FastAPI route and schema metadata in `src/pixelpast/api/`.
The checked-in export at `doc/api/openapi.yaml` is the review-friendly repository artifact derived from that metadata.

## Export Workflow

Refresh the contract with:

```text
pixelpast export-openapi
```

This command deterministically exports the current FastAPI OpenAPI schema to `doc/api/openapi.yaml`.

## Rendering Direction

Static HTML documentation can be rendered from the committed contract with:

```text
npx @redocly/cli build-docs doc/api/openapi.yaml --output doc/api/html/index.html
```

Generated HTML under `doc/api/html/` is not part of the default checked-in artifacts and remains ignored by Git.
