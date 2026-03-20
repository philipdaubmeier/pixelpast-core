# R-036-02 - Spotify JSON Discovery and Account Grouping

## Goal

Implement the intake boundaries for Spotify takeout files and make the
connector's account grouping model explicit before canonical persistence is
introduced.

Spotify history differs from the existing connectors because one logical import
source can span multiple JSON documents. The discovery and staging boundary
must make that workable without collapsing back into a monolithic service.

## Dependencies

- `R-036-01`

## Scope

### Add Spotify Runtime Configuration

Extend shared settings with `PIXELPAST_SPOTIFY_ROOT`.

The setting should support:

- a direct JSON file path
- a directory root for recursive JSON intake

The connector should fail clearly when the Spotify source is invoked without a
configured root.

### Implement Deterministic JSON Discovery

Introduce a discovery component for Spotify streaming-history documents.

At minimum, it should:

- walk the configured root deterministically
- collect `.json` files recursively when a directory is provided
- preserve enough file identity to produce stable progress and error reporting

Do not place parsing logic inside discovery. Discovery should remain concerned
with intake boundaries and deterministic file enumeration.

### Define the Grouping Boundary for Multi-File Imports

Make explicit how later tasks can turn many discovered files into one canonical
source per Spotify username.

The staged workflow should keep document-level discovery, fetch, and transform
explicit, while still making room for an account-level persistence step that
merges all rows belonging to the same username before replacement.

### Add Intake Tests

Add automated coverage for:

- direct-file intake
- recursive directory intake
- deterministic discovery ordering
- clear failure behavior for a missing configured root

## Out of Scope

- no canonical event persistence yet
- no final JSON row transformation yet
- no CLI registration yet

## Acceptance Criteria

- `PIXELPAST_SPOTIFY_ROOT` is part of shared runtime configuration
- a dedicated Spotify discovery component exists
- the discovery path supports both direct-file and recursive-directory intake
- the staged boundary for later account-level grouping is explicitly defined
- automated tests cover discovery ordering and missing-root behavior

## Notes

This task should not try to solve idempotency by itself. Its purpose is to make
the multi-document intake model explicit and testable before lifecycle and
persistence are added.
