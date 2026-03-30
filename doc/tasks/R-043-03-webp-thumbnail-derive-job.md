# R-043-03 - WebP Thumbnail Derive Job

## Goal

Add a dedicated derive job that precomputes fixed WebP thumbnail renditions for
canonical image assets.

The job should support both:

- preparing missing thumbnails ahead of time
- force-rebuilding existing thumbnails when the rendition logic changes

## Dependencies

- `R-043-02`
- `R-028-03`

## Scope

### Introduce A Dedicated Thumbnail Derive Job

Add one derive job responsible for building thumbnails from canonical asset
inputs.

Recommended job identity:

- CLI name: `asset-thumbnails`

The job should use the existing derive-job runtime and progress infrastructure
rather than inventing a separate ad hoc command path.

### Limit Processing To Supported Image Assets

The job should operate only on assets that can produce still-image thumbnails.

The first increment should explicitly skip unsupported asset types rather than
trying to define a generic preview system for every future media type.

### Implement The Fixed Rendition Contract

The derive job must generate exactly these renditions:

- `h120`
  - center-crop source images wider than `3:1` down to `3:1`
  - scale the result to height `120`
- `h240`
  - center-crop source images wider than `3:1` down to `3:1`
  - scale the result to height `240`
- `q200`
  - take the largest centered square crop
  - scale to `200x200`

All outputs must be WebP files.

### Persist Thumbnails Under The Fixed Thumbnail Root

Derived thumbnails should be written under the configured global thumbnail root
using a deterministic path layout based on rendition and asset short id.

Recommended layout:

- `<thumb_root>/h120/<short_id>.webp`
- `<thumb_root>/h240/<short_id>.webp`
- `<thumb_root>/q200/<short_id>.webp`

### Expose Rendition Selection And Rebuild Controls In CLI

The derive job should support:

- selecting one or more renditions to generate
- generating only missing thumbnail files
- force-rebuilding existing files

Recommended CLI direction:

```text
pixelpast derive asset-thumbnails --rendition h120 --rendition q200
pixelpast derive asset-thumbnails --rendition h240 --force
```

Default behavior should be missing-only generation unless `--force` is
explicitly requested.

### Keep Generation Deterministic

Repeated runs over the same asset set should produce stable outputs and stable
write behavior.

The derive job should define:

- how it resolves original files from canonical asset data
- how it handles missing original files
- how it reports skipped, generated, overwritten, and failed outputs

## Out of Scope

- no API route work
- no auth or signed media URLs
- no arbitrary user-supplied size parameters

## Acceptance Criteria

- a dedicated thumbnail derive job exists in the shared derive runtime
- the job supports `h120`, `h240`, and `q200` only
- all generated thumbnails are WebP files
- the CLI can target selected renditions
- the CLI can run in missing-only mode and in force-rebuild mode
- repeated runs remain deterministic and idempotent for missing-only execution

## Notes

This task gives PixelPast an explicit precomputation path for the thumbnail hot
path. Lazy generation may still exist later as an API fallback, but it should
not replace a proper derive job.
