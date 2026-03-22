# R-039-02 - Google Places Derive Loading and Provider Client

## Goal

Implement the input-loading and provider-boundary layer for the new
`google_places` derive job.

## Dependencies

- `R-039-01`
- `R-038-06`

## Scope

### Load Place Candidates from Canonical Events

Add an explicit derive loading path that scans canonical events for a non-empty
`raw_payload.googlePlaceId`.

For each qualifying event, the loader should capture:

- `event_id`
- canonical event identity needed for deterministic linking
- Google place id
- link confidence candidate from canonical payload

The confidence mapping for this series should be:

- `raw_payload.candidateProbability` -> `event_place.confidence`

When that value is absent or non-numeric, the derived confidence should remain
`NULL`.

### Deduplicate Remote Work Before Fetching

The loading or planning stage should build a deterministic unique place-id map
before any provider requests are issued.

That planning result should distinguish at least:

- event count scanned
- event count carrying a Google place id
- unique place id count
- place ids already satisfied by fresh cached rows
- place ids requiring remote refresh

### Resolve the Provider Source Deterministically

Add a small provider-source resolution path that creates or reuses one
deterministic `Source` row for Google Places API provenance.

The intended identity for this series is:

- `type = "google_places_api"`
- `name = "Google Places API"`
- `external_id = "google_places_api"`

No credentials should be stored in this source record.

### Add Runtime Settings for the Google Places Client

Extend runtime settings so the derive job can be configured entirely through
environment variables.

At minimum, define support for:

- required Google Places API credential input
- optional language code
- optional region code
- refresh-age threshold with a default of three years

The naming should be explicit and derive-job-specific, for example using a
`PIXELPAST_GOOGLE_PLACES_...` prefix.

### Introduce a Thin Google Places Client Boundary

Add a dedicated provider client abstraction that resolves one Google place id to
the selected derived snapshot fields:

- external id
- display name
- formatted address
- latitude
- longitude

The client should request only the required Google Places fields for this task.

It should also make remote failure modes explicit so the job can surface clear
partial-failure reporting later.

## Out of Scope

- no database writes to `place` or `event_place` yet
- no CLI entrypoint wiring yet
- no full retry policy framework
- no support for non-Google providers

## Acceptance Criteria

- derive loading scans canonical events by `raw_payload.googlePlaceId`
- the planning step deduplicates remote place-id fetches before API access
- one deterministic provider `Source` row can be created or reused
- runtime settings expose the required Google Places credential and refresh
  configuration
- a thin client boundary exists that maps Google responses onto the selected
  `place` fields only

## Notes

This task should keep the remote provider boundary narrow. The derive job needs
selected place details, not a general-purpose Google SDK wrapper.
