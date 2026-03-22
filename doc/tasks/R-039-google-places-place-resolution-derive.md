# R-039 - Google Places Place Resolution Derive

## Goal

Introduce a dedicated derive job that resolves reusable place records from
canonical events carrying a Google place identifier in `raw_payload`.

The important boundary for this series is:

- the job is Google Places API specific and should be exposed as
  `pixelpast derive google_places`
- the derived storage model must remain provider-agnostic
- canonical `Event` rows must remain unchanged apart from being linked through a
  derived association table

This series should add a reusable derived place cache and an event-to-place
linking model so frequently visited places are stored once and reused across
many events.

## Dependencies

- `R-028-03`
- `R-038-06`

## Scope

### Introduce a Provider-Agnostic Derived Place Model

Add a new derived-owned relational model built around:

- `place`
- `event_place`

For this series, `place` should contain only these fields:

- `id`
- `source_id`
- `external_id`
- `display_name`
- `formatted_address`
- `latitude`
- `longitude`
- `lastupdate_at`

`event_place` should contain only:

- `event_id`
- `place_id`
- `confidence`

No `metadata_json` column should be added to either table in this series.

### Keep the Derived Model Generic but the Job Specific

The new derive job should be explicitly named `google_places`.

Its remote provider behavior is Google specific, but the database model should
avoid baking Google naming into table or column names.

This means:

- `place.external_id` stores the provider-specific place identifier
- `place.source_id` points to a `Source` row representing the provider
- `event_place` remains a generic event-to-place relationship table

### Resolve Place Candidates from Canonical Events

The job should scan canonical events for a non-empty
`raw_payload.googlePlaceId`.

Current Google Maps Timeline visit imports are the expected producer of that
field, but the derive selection rule should stay payload-based rather than
hard-coding `Event.type = "timeline_visit"`.

For each matching event, the job should:

- collect the event id
- collect the Google place id
- collect the best available link confidence from canonical payload

The Google place id set must then be deduplicated before any API work happens.

### Use Refresh-Aware Remote Resolution

The job must resolve each unique place id at most once per run.

Before calling the Google Places API, it must check whether a matching `place`
row already exists for the provider source and external id.

If an existing row is present:

- reuse it without a remote call when `lastupdate_at` is still fresh
- refetch it only when it is older than the configured staleness threshold

The default staleness policy for this series should be three years, expressed
through configuration rather than hard-coded magic in the job body.

### Store Only the Selected Place Snapshot

The derive job should persist only the selected stable place fields needed by
current product behavior:

- provider source reference
- provider place id
- display name
- formatted address
- latitude
- longitude
- refresh timestamp

This series should not persist the full Google Places API response.

### Link Events to Resolved Places Idempotently

After place resolution, the job should ensure every qualifying event is linked
through `event_place`.

The link behavior should be idempotent:

- if the correct link already exists, do not insert a duplicate
- if the link exists but `confidence` changed, update it deterministically
- if an event already has a conflicting derived place link for this use case,
  replace it with the currently resolved target

For v1, `event_place.confidence` should be derived from the canonical
Google Maps Timeline visit payload:

- prefer `raw_payload.candidateProbability`
- leave the field `NULL` when no candidate probability is available

### Represent the Google Provider as a Source Row

The derive path should reuse the existing `source` table to represent the
Google Places provider identity.

The series should define one deterministic provider source record, for example:

- `Source.type = "google_places_api"`
- `Source.name = "Google Places API"`
- `Source.external_id = "google_places_api"`

This row is operational provider provenance for derived place records, not a
user-imported timeline source.

### Configure the Job Through Environment Variables

The derive job should read Google Places configuration from runtime settings and
environment variables rather than from checked-in code or database secrets.

At minimum, the series should cover:

- API key or equivalent credential input
- optional language or region preferences when needed by the client
- configurable staleness threshold with a default of three years

Secrets must not be persisted into `Source.config`.

### Reuse Shared Derive Progress Infrastructure

The job should report phase-aware progress through the same shared progress
runtime already used by ingest and derive.

At minimum, CLI-visible progress should cover these phases:

- collecting place ids
- fetching place details
- persisting places and links

The terminal summary should report meaningful counts such as:

- scanned event count
- unique place id count
- fetched remote place count
- reused cached place count
- inserted place count
- updated place count
- unchanged place count
- inserted event-place link count
- updated event-place link count
- unchanged event-place link count

## Subtasks

- `R-039-01`
  - add the generic `place` and `event_place` derived schema plus repository
    foundations
- `R-039-02`
  - implement canonical input loading, provider-source resolution, Google
    Places client boundaries, and runtime settings
- `R-039-03`
  - persist refreshed place rows and idempotent `event_place` links using the
    selected confidence mapping
- `R-039-04`
  - wire `pixelpast derive google_places`, shared progress reporting, and
    end-to-end coverage

## Out of Scope

- no changes to canonical `Event.title`
- no persistence into canonical `Event.derived_payload`
- no generic multi-provider place-resolution framework
- no reverse-geocoding fallback for events without `googlePlaceId`
- no UI work
- no map-radius query APIs yet
- no full raw-response archival of Google Places payloads
- no background scheduling changes

## Acceptance Criteria

- a documented `R-039` task series exists for Google Places-based place
  resolution
- the series introduces a provider-agnostic derived place model using `place`
  and `event_place`
- the series explicitly requires the derive job to scan canonical events by
  `raw_payload.googlePlaceId`
- the series explicitly requires unique place-id collection before remote API
  calls
- the series explicitly requires refresh-aware reuse of cached places based on
  `lastupdate_at`
- the series explicitly requires idempotent event-to-place linking through
  `event_place`
- the series explicitly requires CLI exposure as `pixelpast derive
  google_places`
- the series explicitly requires reuse of the shared progress infrastructure
  from `src/pixelpast/shared`

## Notes

This series intentionally treats provider-specific place lookup as a derive
concern, not as canonical enrichment during ingest.

That preserves the Raw -> Canonical -> Derived separation while still allowing
timeline visits to gain better display names and reusable place references in
read models later.
