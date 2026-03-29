# R-041-06 - Shared Ingestion Persister Helpers

## Goal

Reduce duplicated canonical persistence boilerplate inside ingestion persisters
without changing repository boundaries or connector semantics.

Two repetition clusters are now visible:

- asset-oriented persisters for photos and Lightroom
- source-plus-event replacement persisters for calendar, Spotify, Google Maps
  Timeline, and workdays vacation

This task should extract small shared helpers for those clusters where the
duplication is mechanical rather than semantic.

## Dependencies

- `R-041-03`

## Scope

### Extract Shared Helpers for Asset-Oriented Persisters

Identify the repeated mechanics currently shared by the photo and Lightroom
asset persisters, such as:

- creator-person lookup
- asset upsert invocation
- tag creation and replacement
- person creation and replacement
- deterministic inserted / updated / unchanged resolution

Extract only the mechanical parts that are genuinely identical today.

### Extract Shared Helpers for Source-and-Event Replacement Persisters

Identify the repeated mechanics currently shared by event-oriented source
persisters, such as:

- source upsert by external id
- `replace_for_source(...)` event persistence
- `count_missing_from_source(...)` preview calls
- required source-external-id validation

Keep connector-specific event payload shaping explicit where fields differ, for
example:

- latitude and longitude handling
- raw payload augmentation
- skipped-event counts
- source naming defaults

### Prefer Small Helpers over Deep Inheritance

This task should favor small shared helpers, value objects, or narrow base
classes over a deep hierarchy.

The connector-specific persister modules should remain easy to read in isolation
and should still make their payload-shaping decisions obvious.

## Out of Scope

- no repository API changes
- no canonical schema changes
- no connector-specific event-shape normalization

## Acceptance Criteria

- duplicated mechanical persistence logic is reduced across the asset-oriented
  and event-oriented persister families
- connector-specific payload shaping remains explicit and local
- repository boundaries and persistence semantics remain unchanged

## Notes

This is deliberately a second-wave cleanup task. The risk of over-abstracting is
higher here than in the service, progress, or lifecycle layers, so the helpers
should stay narrow.
