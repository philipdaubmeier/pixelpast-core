# R-008 - Vertical Slice Hardening and Domain Decision

## Goal

Harden the first implemented vertical slice against the original architectural
plan and make the package structure intentional before more slices are added.

This task should turn current conventions into enforced behavior, especially for
idempotent ingestion and test coverage, and explicitly decide whether the
`domain/` package has a real role yet.

---

## Scope

Implement the following hardening work:

- enforce database-level uniqueness for natural keys currently treated as unique
  by repository code
- align ingestion persistence access more cleanly with the repository boundary
- add missing automated tests for the first vertical slice
- make an explicit structural decision about the `domain/` package:
  - either remove it if it is still empty and unused
  - or introduce a narrowly justified first use for it with business-facing,
    persistence-independent types

At minimum, review and address:

- `Asset.external_id` as the idempotent upsert key
- `Source.type` if it is intended to identify one configured source per
  connector type
- ingestion run behavior across successful, repeated, empty, and partial-failure
  executions
- the current direct ORM/session access inside ingestion orchestration

If `domain/` is kept, it must not be a placeholder package. It should contain
something that is meaningfully independent of both ORM and API concerns, for
example:

- domain enums
- value objects
- business-facing type definitions
- pure domain policies

If that justification does not exist yet, remove the package for now.

---

## Out of Scope

- No new connector
- No UI changes
- No broad package reorganization beyond the explicit `domain/` keep-or-remove
  decision
- No speculative domain abstraction without immediate use
- No expansion of the analytics model beyond what is needed for hardening tests

---

## Acceptance Criteria

- repeated ingestion is enforced as idempotent by both repository logic and
  database constraints
- duplicate `Asset` rows cannot be created for the same `external_id`
- source identity rules are explicit and enforced consistently in schema and
  repository behavior
- ingestion orchestration no longer relies on ad hoc direct ORM access where a
  repository-owned access path is more appropriate
- automated tests exist for:
  - repeated execution
  - empty source input
  - partial failure behavior
  - API read behavior for the implemented timeline endpoints
- the repository contains an explicit decision on `domain/`:
  - either the package is removed
  - or it contains a justified first set of persistence-independent domain
    types

---

## Notes

This is a hardening task, not a feature-expansion task.

The main purpose is to lock in the architectural intent of the first slice
before additional connectors and derived jobs multiply accidental structure.

The review behind this task identified three main gaps:

- idempotency is currently treated as an application convention rather than a
  schema-enforced guarantee
- the repository boundary is mostly respected but not fully clean in ingestion
  orchestration
- the `domain/` package currently appears to be a placeholder rather than an
  active architectural layer
