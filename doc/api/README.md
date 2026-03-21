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

This command deterministically exports the current FastAPI OpenAPI schema to
`doc/api/openapi.yaml` and then renders static HTML documentation to
`doc/api/html/index.html`.

Generated HTML under `doc/api/html/` is not part of the default checked-in
artifacts and remains ignored by Git.

## Sync Check

```text
pixelpast export-openapi --check --no-render
```

Use this in CI to fail when the committed OpenAPI contract is stale without
rewriting repository files.

## Rendering Toolchain

Static HTML rendering is performed via Redocly CLI from the committed
`doc/api/openapi.yaml` contract. The CLI command uses:

```text
npx @redocly/cli build-docs doc/api/openapi.yaml --output doc/api/html/index.html
```
