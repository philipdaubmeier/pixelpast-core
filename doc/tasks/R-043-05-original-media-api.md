# R-043-05 - Original Media API

## Goal

Expose a short-id-based route for original-image delivery that resolves the
canonical asset through the database and returns the original filename through
`Content-Disposition`.

Unlike thumbnail delivery, this route is allowed to pay the cost of a canonical
lookup because original-file access is not the dominant high-frequency path.

## Dependencies

- `R-043-02`

## Scope

### Introduce A Short-ID-Based Original Route

Add a public route for original image delivery:

- `GET /media/orig/{short_id}`

The route should resolve the canonical asset through the database using the
public short id.

### Resolve The Original File Through Canonical Provenance

The route must map the resolved asset back to its source-specific file
provenance and locate the original file on disk.

The resolution path may combine:

- source-scoped configuration from `Source.config`
- canonical asset metadata carrying normalized file provenance

The important boundary is that the route resolves the real original file from
canonical data rather than from a public filesystem path supplied by the
request.

### Preserve The Original Filename In The Response

The response should include `Content-Disposition` carrying the original file
name.

The first increment should preserve the name for browser download behavior while
still allowing the route to be used for opening the full-size image.

### Define Missing-Asset And Missing-File Behavior

The route should explicitly define behavior for:

- unknown short ids
- resolved assets whose original file no longer exists
- assets that cannot resolve to a valid original-file path

Failures should be explicit and deterministic.

### Document The Route Contract

The original-media route should be documented through the same API contract
workflow as the rest of the backend surface.

The documented contract should cover:

- route shape
- representative success behavior
- filename-preserving response headers
- important not-found cases

This task should produce API documentation quality analogous to the existing
documented endpoints rather than leaving the media route outside the normal API
documentation surface.

## Out of Scope

- no folder ZIP export in this task
- no auth or signed URLs yet
- no alternative public path-based original route

## Acceptance Criteria

- a short-id-based original-media route exists
- the route resolves assets through the canonical database using `short_id`
- the original file is resolved from persisted canonical provenance
- the response includes `Content-Disposition` carrying the original filename
- error behavior is defined for missing assets and missing original files
- the route contract is documented through the repository's normal API
  documentation flow at the same level of completeness as the other public API
  endpoints

## Notes

This task intentionally keeps original delivery separate from the thumbnail hot
path. Correctness and filename preservation matter more here than avoiding the
canonical lookup.
