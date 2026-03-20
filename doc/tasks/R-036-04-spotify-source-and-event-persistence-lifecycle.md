# R-036-04 - Spotify Source and Event Persistence Lifecycle

## Goal

Persist canonical Spotify sources and music-play events through the same
repository and lifecycle seams already used by the other connectors, while
preserving account-scoped idempotency across multiple takeout files.

## Dependencies

- `R-036-03`

## Scope

### Add Spotify Persistence Behind Repositories

Introduce repository-backed Spotify persistence components rather than placing
database logic in the connector.

At minimum, the persistence layer should be able to:

- resolve or create the canonical Spotify `Source` by `external_id`
- replace canonical `Event` rows for that source
- commit or rollback one ingestion transaction

If no repository seam exists for canonical events that fits this connector,
extend the repository layer rather than persisting inline from a service or
connector class.

### Use Account-Scoped Full Replacement for v1 Idempotency

The first Spotify increment should stay idempotent without inventing a fragile
per-stream upsert identity.

The acceptable v1 behavior is:

- collect the full transformed event set for one username across all discovered
  files in the run
- resolve or create the canonical source for that username
- delete existing events for that source
- insert the full replacement set in deterministic order

Repeated imports of the same file set should therefore leave the database in
the same final state.

### Introduce a Spotify Run Coordinator

Add a Spotify-specific lifecycle collaborator analogous to the other ingest
coordinators.

It should own:

- run creation
- initial progress state
- account-level reconciliation needed before persistence

Do not move direct database writes into the connector facade.

### Preserve Multi-Document Account Semantics

If a run discovers multiple JSON files for the same username, the connector
must merge them into one source replacement set rather than replacing the
source separately per file.

This behavior should be explicit and covered by tests, because it is the main
structural difference between Spotify history and the current calendar ingest
model.

### Define v1 Duplicate Semantics Explicitly

Do not invent heuristic de-duplication rules for nearly matching stream rows.

For v1:

- each input row remains one canonical event candidate
- idempotency is achieved through deterministic full replacement of the
  account's event set

If the same exact row appears twice in the source documents, both rows remain
present unless a later task series introduces a stronger product requirement.

## Out of Scope

- no CLI registration yet
- no Spotify API enrichment
- no generalized per-stream upsert identity scheme

## Acceptance Criteria

- Spotify persistence is implemented behind repository and lifecycle
  collaborators, not inline in the connector
- the Spotify ingest path preserves one canonical source per account username
- repeated imports of the same takeout file set are idempotent through
  account-scoped replacement
- one run can merge multiple JSON files into one account-level replacement set
- a Spotify run coordinator exists and uses the shared progress runtime
- the v1 duplicate-row behavior is explicitly documented and tested

## Notes

This task is where the Spotify connector proves that the staged ingest shell is
reusable even when source identity is broader than one discovered file.
