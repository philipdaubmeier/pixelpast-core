# R-039-04 - Google Places CLI, Progress, and End-to-End Tests

## Goal

Wire the new `google_places` derive job into the CLI, shared progress runtime,
and end-to-end regression suite.

## Dependencies

- `R-039-03`
- `R-028-03`

## Scope

### Expose the Job Through the Existing Derive Entrypoint

Add the new derive job to the shared derive entrypoint surface so it is
available through:

- `pixelpast derive google_places`
- the supported derive-job listing
- `pixelpast derive --help`

The derive implementation should remain job-specific rather than introducing a
generic provider-job framework.

### Reuse Shared Progress Infrastructure

The job must reuse the existing shared progress classes under
`src/pixelpast/shared`, especially the generic phase-aware persistence and CLI
callback pattern already used by other operational jobs.

At minimum, the CLI-visible progress should expose these phases:

- collecting place ids
- fetching place details
- persisting places and links

### Report a Useful Terminal Summary

The derive command output should report a useful terminal summary including at
least:

- scanned event count
- qualifying event count
- unique place id count
- remote fetch count
- cached reuse count
- inserted place count
- updated place count
- unchanged place count
- inserted event-place link count
- updated event-place link count
- unchanged event-place link count

### Cover the Job End to End

Add automated coverage that exercises at least:

- successful resolution of events carrying repeated Google place ids
- one-run deduplication so each unique place id is fetched at most once
- cached-place reuse without remote refetch when `lastupdate_at` is still fresh
- stale-place refetch when `lastupdate_at` exceeds the configured age threshold
- idempotent repeated derive runs with unchanged canonical inputs
- event-place link creation with confidence mapped from
  `raw_payload.candidateProbability`
- `NULL` confidence when the canonical payload lacks candidate probability
- partial or hard failure behavior when Google client configuration is missing
  or the provider call fails

### Keep External API Use Mocked in Tests

The regression suite should not depend on live Google API access.

Tests should use a narrow fake or stub client so behavior is pinned
deterministically and does not require network access or paid credentials.

## Out of Scope

- no UI changes
- no read-model projection changes yet
- no live integration test against the real Google API

## Acceptance Criteria

- `pixelpast derive google_places` is available through the shared CLI entrypoint
- progress reporting reuses the shared progress infrastructure instead of adding
  a parallel mechanism
- CLI output reports the three requested operational phases
- terminal summaries report both place-row and event-place-link outcomes
- end-to-end tests cover deduplication, cache reuse, stale refresh, idempotent
  reruns, and confidence mapping

## Notes

This task is where the new place-resolution derive job becomes part of the
normal operational workflow rather than only a persistence capability.
