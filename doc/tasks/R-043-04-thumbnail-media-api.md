# R-043-04 - Thumbnail Media API

## Goal

Expose short-id-based thumbnail routes that serve fixed WebP renditions with
minimal request overhead for the common browsing case.

This task should make thumbnail requests cheap when the derived file already
exists while still allowing a controlled lazy fallback when it does not.

## Dependencies

- `R-043-02`
- `R-043-03`

## Scope

### Introduce Fixed Thumbnail Routes

Add a thumbnail media surface using the asset short id and the fixed rendition
names.

The intended public route contract is:

- `GET /media/h120/{short_id}.webp`
- `GET /media/h240/{short_id}.webp`
- `GET /media/q200/{short_id}.webp`

No additional thumbnail sizes should be routable in v1.

### Optimize Cache Hits For Filesystem Delivery

When the requested thumbnail file already exists under the configured thumbnail
root, the request path should serve it without first querying the canonical
database.

That is the main optimization target of this task.

### Allow Lazy Fallback On Thumbnail Miss

When the requested thumbnail file does not exist yet, the API may fall back to
database-backed asset resolution by `short_id` and generate the missing
thumbnail on demand.

The fallback path should:

- validate that the short id resolves to a real asset
- validate that the asset supports image-thumbnail generation
- generate only one of the allowed fixed renditions
- persist the generated WebP file into the thumbnail root
- return the generated thumbnail response

### Reuse The Thumbnail Generation Implementation

The lazy fallback path must reuse the same thumbnail-generation implementation
introduced for the dedicated derive job.

Required constraints:

- no separate ad hoc image-processing pipeline inside the API route
- no duplication of rendition logic between derive and API layers
- the fixed crop and scale rules for `h120`, `h240`, and `q200` must come from
  one shared implementation boundary

The API route may orchestrate lookup and response behavior, but thumbnail
generation itself should be delegated to the same reusable service or helper
used by `R-043-03`.

### Define Error Behavior Explicitly

The thumbnail API should define deterministic behavior for:

- unknown short ids
- unsupported assets
- missing original files
- invalid rendition paths

The route surface should fail clearly rather than silently returning wrong media
or generic placeholders.

### Document The Media Contract

The new routes should be documented like the rest of the backend API surface
through the repository's normal OpenAPI export workflow.

The important response contract is:

- content type `image/webp`
- route identity based on fixed rendition plus `short_id`
- representative success and important not-found examples

This task should produce API documentation quality analogous to the existing
documented endpoints rather than leaving the media routes undocumented or
described only informally.

## Out of Scope

- no auth or signed thumbnail URLs yet
- no arbitrary resize parameters
- no original-media delivery in this task

## Acceptance Criteria

- short-id-based thumbnail routes exist for `h120`, `h240`, and `q200`
- thumbnail cache hits can be served without a canonical database lookup
- cache misses can lazily generate and persist the requested allowed rendition
- lazy fallback generation reuses the shared thumbnail-generation logic from the
  derive job rather than duplicating image-processing code in the API layer
- all thumbnail responses use WebP output
- failure behavior is defined for missing assets and missing originals
- the route contract is documented with the repository's normal API
  documentation flow at the same level of completeness as the other public API
  endpoints
- no duplicate code paths for thumbnail generation, code must reuse the methods
  of thumbnail derive job

## Notes

This task is about the browsing hot path. The main success condition is that
existing thumbnail files behave like cheap static assets while still preserving
correctness on first access.
