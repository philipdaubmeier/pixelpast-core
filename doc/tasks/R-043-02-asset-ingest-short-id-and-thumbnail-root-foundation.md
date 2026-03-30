# R-043-02 - Asset Ingest Short ID and Thumbnail Root Foundation

## Goal

Ensure every asset-ingest write path generates and preserves canonical short
ids, and require explicit thumbnail-storage configuration before asset ingest is
allowed to run.

This task translates the schema introduced in `R-043-01` into the existing
asset-ingest runtime boundaries.

## Dependencies

- `R-043-01`

## Scope

### Generate Short IDs At The Asset Write Boundary

All asset persistence paths should assign a short id when inserting a new
canonical asset row.

The preferred responsibility boundary is the shared write repository or a
repository-owned collaborator rather than duplicating id generation inside each
connector.

Required behavior:

- new asset inserts receive a generated `short_id`
- updates of an existing asset preserve the previously assigned `short_id`
- repository-side retries handle rare uniqueness collisions cleanly

### Cover All Current Asset Ingest Paths

The current asset-ingest connectors should flow through the new behavior:

- photo ingest
- Lightroom catalog ingest

If additional asset-ingest entrypoints already write canonical assets through
shared helpers, they should inherit the same short-id behavior without
connector-specific duplication.

### Require A Fixed Thumbnail Root In Runtime Settings

Introduce a dedicated runtime setting for the global thumbnail-storage root.

Recommended direction:

- `Settings.media_thumb_root`
- environment variable `PIXELPAST_MEDIA_THUMB_ROOT`

This root represents the one fixed filesystem location where derived thumbnail
files will be stored for all asset sources.

### Fail Fast Before Asset Ingest Without Thumbnail Storage

Any command path that writes canonical assets must validate that the thumbnail
root is configured and usable before ingest work begins.

That includes:

- configuration presence
- path normalization and resolution
- clear failure messaging when the setting is missing

The system should not partially ingest new assets and only fail later during
thumbnail work.

### Preserve Original File Provenance Needed Later For Original Delivery

This task should also make the later original-media route feasible.

The asset-ingest write model must preserve the filesystem provenance needed to
resolve the original file from a short id later. That may continue to live in:

- `Source.config` for source-scoped roots
- asset metadata payloads for relative or connector-specific file provenance

The important requirement is that current asset connectors persist enough
normalized information for later short-id-to-original-file resolution.

## Out of Scope

- no thumbnail derive job yet
- no thumbnail delivery API yet
- no original-media delivery API yet

## Acceptance Criteria

- all new canonical assets written through ingest receive a `short_id`
- existing assets updated by ingest keep their current `short_id`
- photo and Lightroom asset ingest paths participate in the new behavior
- a dedicated thumbnail-root runtime setting is defined
- asset ingest fails fast with a clear error if the thumbnail root is not
  configured or not usable
- current asset-ingest persistence keeps the original-file provenance needed for
  later original delivery

## Notes

This task deliberately centralizes short-id creation in the persistence layer so
connectors remain focused on discovery and transformation rather than on public
identifier policy.
