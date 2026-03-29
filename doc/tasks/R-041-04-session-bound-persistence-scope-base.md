# R-041-04 - Session-Bound Persistence Scope Base

## Goal

Reduce the repeated transaction-boundary boilerplate in staged ingestion
`PersistenceScope` adapters.

The current connector-specific persistence scopes all repeat the same session
lifecycle shell:

- create a session from runtime
- commit
- rollback
- close

This task should extract that common shell while keeping connector-specific
repository wiring and missing-from-source logic explicit.

## Dependencies

- none

## Scope

### Introduce a Small Shared Persistence-Scope Base

Create a minimal reusable base or helper for staged ingestion persistence
scopes.

It should own only the repeated session lifecycle mechanics:

- session creation
- commit
- rollback
- close

Avoid a broad abstraction that tries to normalize all repository wiring or
candidate types.

### Keep Connector-Specific Persistence Explicit

Each connector-specific scope should still explicitly define:

- its repositories
- its persister collaborator
- its missing-from-source calculation
- its `persist(candidate=...)` implementation

The goal is to remove lifecycle boilerplate, not to hide connector-specific
persistence behavior.

### Preserve the Existing Staged Runner Contract

The generic staged runner protocol must remain stable.

Do not change the current required persistence-scope responsibilities:

- count missing from source
- persist one candidate
- commit
- rollback
- close

## Out of Scope

- no staged-runner redesign
- no repository-boundary changes
- no connector-specific persistence refactors beyond the shared shell

## Acceptance Criteria

- the repeated session lifecycle boilerplate is centralized in one shared base
  or helper
- connector-specific persistence scopes remain explicit at the repository and
  candidate level
- staged-runner behavior and transaction semantics remain unchanged

## Notes

This should stay small. A lightweight shared transaction shell is enough; a
generic persistence framework would be overreach here.
