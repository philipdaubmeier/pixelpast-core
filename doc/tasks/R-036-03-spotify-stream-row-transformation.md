# R-036-03 - Spotify Stream Row Transformation

## Goal

Transform Spotify takeout rows into canonical source and event candidates while
keeping the connector faithful to the project's chronology-centered event
model.

This task is where the canonical mapping becomes executable.

## Dependencies

- `R-036-01`
- `R-036-02`

## Scope

### Parse Streaming-History Documents

Introduce Spotify transform helpers that can:

- load one discovered JSON document into row dictionaries
- validate that the payload is a streaming-history array
- convert each valid row into a typed parsed-row contract
- surface document-level transform errors without pushing persistence concerns
  into transform code

### Build Canonical Spotify Source Candidates

Add a transform helper that derives one canonical source candidate per
username.

For v1:

- `Source.type` should be `spotify`
- `Source.external_id` should be a stable username-based identity
- the source name should be deterministic and human-readable

If one document contains rows for more than one username, the transform output
should make that visible rather than silently assuming a single account.

### Build Canonical Music-Play Event Candidates

Each imported Spotify row should become one canonical `Event` candidate with:

- `type = "music_play"`
- `timestamp_end` parsed from `ts`
- `timestamp_start = timestamp_end - ms_played`
- `title = "{artist} - {title}"` when both metadata fields are available
- empty title in v1 when the artist/title pair cannot be formed
- empty summary in v1
- canonical `raw_payload` containing only:
  - `username`
  - `platform`
  - `conn_country`
  - `spotify_track_uri`
  - `spotify_episode_uri`
  - `shuffle`
  - `skipped`

The transform layer must not preserve the full original row as canonical raw
payload.

### Define Deterministic Ordering

Because the v1 persistence model will use source-scoped replacement, the
transform output must be order-stable.

Define and test one deterministic sort order for canonical event candidates,
for example by:

- normalized username
- `timestamp_end`
- discovered document path
- row index within the document

## Out of Scope

- no database persistence yet
- no source replacement logic yet
- no CLI integration yet

## Acceptance Criteria

- Spotify transform helpers exist for document parsing, source-candidate
  creation, and event-candidate creation
- canonical source candidates use `type = "spotify"`
- canonical event candidates use `type = "music_play"`
- canonical title, summary, timestamp, and `raw_payload` mapping rules are
  covered by tests
- transform output ordering is deterministic and covered by tests
- the transform layer does not persist the full takeout row into canonical
  storage

## Notes

This task should keep the transform layer narrow and explicit. Do not hide
source grouping, progress updates, or transaction behavior inside row-mapping
helpers.
