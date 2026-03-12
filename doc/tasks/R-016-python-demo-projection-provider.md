# R-016 - Python Demo Projection Provider

## Goal

Move runtime mock ownership from TypeScript into the Python API layer.

The application should be able to run against a deterministic demo provider
without requiring a separate Node mock server or a duplicated frontend-only
business mock.

---

## Scope

Implement an explicit API-side demo provider that can be selected by settings.

The demo provider should serve the same public response contracts as the
database-backed implementation for:

- `GET /exploration`
- `GET /days/{date}/context`

The demo output should remain meaningfully explorable and cover:

- multiple full years
- non-trivial persons and tags
- map points with real coordinates
- all four current view modes

The provider should be:

- deterministic across runs
- isolated from production data access
- usable by the UI without transport-level branching

Once this exists:

- remove TypeScript runtime mock data from the live application path

---

## Out of Scope

- no database seeding workflow in this task unless strictly required by the
  chosen implementation
- no duplicate demo logic in both TypeScript and Python
- no production fallback that silently mixes demo and real data
- no UI integration work beyond removing runtime dependence on frontend mocks

---

## Acceptance Criteria

- the Python API can serve high-quality demo exploration data without a Node
  mock server
- demo responses use the exact same schemas as real responses
- demo output is deterministic across runs
- the current UI can remain meaningfully explorable against demo data
- TypeScript runtime mocks are no longer required as a live application data
  source
- provider behavior is covered by tests

---

## Notes

This task exists to remove duplicate runtime mock ownership.
If frontend tests later need fixtures, keep them narrow and test-only rather
than using them as the live application data source.
