# R-041-03 - Shared Persistence Outcome Summary

## Goal

Centralize the internal wire format used between ingestion persisters and
progress trackers for persistence outcomes.

Several connectors currently compose semicolon-delimited outcome strings during
persistence and then parse the same structure again inside progress state
updates. That creates a duplicated hidden protocol spread across multiple
modules.

This task should replace that duplication with one explicit shared serializer
and parser while preserving the current behavior.

## Dependencies

- none

## Scope

### Introduce an Explicit Outcome Summary Model

Create a shared internal representation for persistence outcomes, for example a
small dataclass or value object.

It should be able to carry the current connector needs, including:

- inserted
- updated
- unchanged
- skipped
- failed when relevant
- missing-from-source when relevant
- persisted event or asset counts when relevant

### Preserve the Existing Wire Semantics

If current connector boundaries still expect string outcomes, the new shared
model may continue to serialize to the same string format for now.

What matters is that:

- formatting is centralized
- parsing is centralized
- connector modules no longer reimplement the same tiny protocol

Do not change the externally visible result contracts or persisted progress
payloads.

### Apply the Shared Contract to Existing Connectors

Use the shared outcome-summary implementation in both directions:

- persisters composing outcomes
- progress trackers consuming outcomes

Cover at least the current connector families:

- calendar
- Spotify
- Google Maps Timeline
- workdays vacation
- Lightroom catalog

## Out of Scope

- no semantic change to persistence outcomes
- no public API exposure of the internal summary object
- no result-schema cleanup beyond the internal refactor

## Acceptance Criteria

- one shared implementation owns formatting and parsing of connector persistence
  outcomes
- connector modules no longer duplicate outcome-string parsing and composition
- the existing progress payloads and result counts remain unchanged
- the internal protocol becomes explicit and testable

## Notes

This task is intentionally internal. The target is duplicated hidden coupling,
not a redesign of ingest result modeling.
