# R-022-05 - Photo Asset Persistence Extraction

## Goal

Remove canonical asset persistence logic from
`ingestion/photos/service.py`.

The service currently owns:

- creator person lookup
- asset upsert
- tag creation
- asset-tag replacement
- person creation
- asset-person replacement
- persistence outcome resolution

That logic belongs to a dedicated persistence collaborator so the service can
focus on orchestration.

## Dependencies

- `R-022-01`

## Scope

### Introduce a Dedicated Photo Asset Persister

Create a component such as `PhotoAssetPersister` that accepts the repositories
it needs and persists one `PhotoAssetCandidate`.

It should own:

- creator person resolution
- asset upsert execution
- tag materialization
- asset-tag link replacement
- person materialization
- asset-person link replacement
- deterministic persistence outcome calculation

### Move `_resolve_persistence_outcome(...)`

The current persistence-outcome logic should move with the persister. The
service should not continue to own persistence semantics.

### Preserve Repository Boundaries

This extraction must continue to respect the architecture rules:

- no direct database logic inside connectors
- no repository access from the UI or entrypoints
- persistence remains behind service/repository boundaries

### Keep Transaction Semantics Stable

The ingest run should still behave as it does today:

- one fatal persistence failure rolls back canonical asset writes for the run
- partial metadata-analysis failures still allow a `partial_failure` terminal
  status when persistence succeeds for the analyzable assets

## Out of Scope

- no import-run lifecycle extraction yet
- no generic progress framework yet
- no generic media-asset persister abstraction yet

## Acceptance Criteria

- idempotency tests still pass unchanged
- `updated` versus `unchanged` semantics still pass unchanged
- fatal persistence failure rollback behavior still passes unchanged
- `PhotoIngestionService` no longer contains repository-level asset persistence
  details

## Notes

Keep this task photo-specific. A later task may extract a reusable asset
persister, but that should not be done before the photo-specific seam is proven
clean.
