# R-036 - Spotify Streaming History Event Ingest

## Goal

Introduce a Spotify ingestion connector that imports GDPR takeout streaming
history JSON files into canonical `Event` rows and extends the daily-aggregate
derive flow with a dedicated Spotify source-scoped `daily_view`.

Unlike the photo connector, this ingest path creates canonical `Event` rows and
does not create `Asset` rows. Unlike the calendar connector, one logical import
source may span multiple JSON documents, while still representing one canonical
Spotify account source. However, like the calendar connector, the provided path
may refer to either one json file, a directory that has to be searched recursively
or a zip file that has to be traversed recursively and stream processed without
extracting its contents to a temporary directory. The connector must only accept
files with the pattern `Streaming_History_Audio*.json` (which must result in
type `music_play` events) and the pattern `Streaming_History_Video*.json` (which
must result in type `video_play` events accordingly). Any other found json files
in the given directory or zip file that do not match these patterns must be
ignored and clearly communicated via CLI output how many json files were skipped
due to this reason.

This task series must reuse the ingestion architecture already established by
the existing connectors wherever that reuse is justified:

- staged orchestration
- shared progress reporting
- lifecycle coordination
- thin connector facade
- persistence behind repository boundaries

The implementation should remain split into focused Python modules such as:

- `contracts.py`
- `discovery.py`
- `fetch.py`
- `transform.py`
- `persist.py`
- `lifecycle.py`
- `progress.py`
- `staged.py`
- `connector.py`
- `service.py`

## Dependencies

- `R-022-08`
- `R-022-09`
- `R-025`
- `R-029`
- `R-031-03`

## Scope

This task series should introduce a new `spotify` ingest source with the
following first-version behavior:

- `PIXELPAST_SPOTIFY_ROOT` accepts:
  - a direct `.json` streaming-history file
  - a directory, in which case nested `.json` files are processed recursively
- one canonical `Source` should represent one Spotify account history import
- canonical `Source.type` should be `spotify`
- canonical `Event.type` should be `music_play`
- no canonical `Asset` rows are created
- no Spotify Web API enrichment is performed during v1 ingest

### Canonical Mapping Direction

For the first increment, Spotify rows must map into the existing canonical
event model as follows:

- `ts` -> `Event.timestamp_end` in UTC
- `ts - ms_played` -> `Event.timestamp_start` in UTC
- `master_metadata_album_artist_name` and `master_metadata_track_name`
  - when both values are present after trimming, write
    `"{artist} - {title}"` into `Event.title`
  - otherwise, keep `Event.title` empty in v1 rather than inventing fallback
    text
- `Event.summary` remains empty in v1
- `raw_payload` stores only:
  - `username`
  - `platform`
  - `conn_country`
  - `spotify_track_uri`
  - `spotify_episode_uri`
  - `shuffle`
  - `skipped`

The following source fields are intentionally not persisted into canonical
`raw_payload` for v1:

- `ip_addr_decrypted`
- `user_agent_decrypted`
- `reason_start`
- `reason_end`
- `offline`
- `offline_timestamp`
- `incognito_mode`
- album, show, and episode labels beyond the title rule above

### Source Identity Direction

The connector should reuse one canonical `Source` per Spotify account.

For v1, source identity should come from the normalized Spotify `username`
present in the takeout rows. The canonical source should therefore reuse one
stable `Source.external_id`, for example `spotify:<username>`, so repeated
imports of the same account history remain attached to the same source.

### Idempotency Direction

Spotify takeouts do not expose an obvious stable per-stream identifier.

The first acceptable idempotency model is therefore account-scoped full
replacement:

- gather the full transformed event set for one account across all discovered
  JSON files in the run
- resolve or create the canonical Spotify source for that account
- delete existing events for that source
- insert the newly transformed event set in deterministic order

This keeps repeated imports deterministic without inventing a weak per-stream
upsert identity that might collapse legitimate repeated plays.

### Daily View Direction

The daily-aggregate derive path should expose Spotify activity as a source-aware
derived view:

- the new `daily_view.source_type` should be `spotify`
- Spotify canonical events should still contribute to the existing overall
  activity view
- the Spotify-specific view should use the regular score-based metadata path,
  not direct-color behavior

## Subtasks

- `R-036-01`
  - define Spotify ingest contracts and characterize takeout fixtures
- `R-036-02`
  - implement Spotify JSON discovery, intake boundaries, and account grouping
- `R-036-03`
  - transform Spotify stream rows into canonical source and event candidates
- `R-036-04`
  - persist Spotify sources and events through an idempotent lifecycle
- `R-036-05`
  - wire CLI and entrypoints, expose progress, and add end-to-end tests
- `R-036-06`
  - extend daily-view metadata and daily-aggregate derive for Spotify

## Out of Scope

- no Spotify API calls or token-based enrichment
- no canonical track, album, episode, or artist catalog tables
- no `Asset` creation for streamed tracks or episodes
- no `Tag`, `Person`, or geolocation enrichment for Spotify rows
- no source-specific UI work beyond what existing `daily_view`-driven surfaces
  already provide
- no attempt to preserve the full original row in canonical `raw_payload`

## Acceptance Criteria

- a documented task series exists for the first Spotify streaming-history
  connector
- the series explicitly states that Spotify history is imported as canonical
  `Event` rows with `type = "music_play"` and not as `Asset` rows
- the series explicitly states that canonical source partitioning for derived
  daily views uses `Source.type = "spotify"`
- the series explicitly requires `timestamp_start` and `timestamp_end` to be
  derived from `ts` and `ms_played`
- the series explicitly limits canonical `raw_payload` to the selected fields
- the series explicitly requires account-scoped idempotent replacement rather
  than ad-hoc per-stream upserts
- the series explicitly requires reuse of the staged ingest and shared progress
  architecture already established by the existing connectors
- the series explicitly covers the new Spotify source-scoped `daily_view`

## Notes

`doc/tasks/R-036-appendix.md` should be treated as the initial field-level
characterization anchor for the Spotify row format. The implementation should
still add local ingest fixtures and executable tests rather than relying on the
appendix alone.
