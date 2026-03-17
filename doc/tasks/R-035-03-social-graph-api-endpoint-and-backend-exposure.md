# R-035-03 - Social Graph API Endpoint and Backend Exposure

## Goal

Expose the social-graph projection through a dedicated REST endpoint with an
explicit API schema and provider path.

This task turns the read model from `R-035-02` into a stable UI-facing
contract.

## Dependencies

- `R-017`
- `R-035-02`

## Scope

### API Contract Direction

Add a dedicated social-graph endpoint, for example under a new `/social` API
surface, that returns the graph projection as explicit response schemas.

The endpoint must not leak ORM rows or internal repository structures.

### Provider Direction

Introduce the provider composition needed to:

- call the canonical social-graph repository read path
- map the repository output into API schemas
- return deterministic JSON for the frontend

### Filter Direction

The endpoint should define a narrow and explicit first-pass filter contract.

At minimum, the implementation must document which persistent global filters
are supported by the social graph in this increment and which are not.

If a filter dimension is unsupported, the behavior must be explicit and
deterministic. The backend and UI must not silently half-apply it.

An acceptable first pass is:

- support canonical filter dimensions that can be interpreted cleanly on asset
  data
- defer unsupported dimensions, such as tag-path filtering if the asset-side
  read path is not yet included, to follow-up work

### Test Direction

Add backend tests for:

- successful graph response shape
- deterministic person and link ordering
- empty-graph behavior
- any supported query filters

## Out of Scope

- no force-layout coordinates in the response
- no graph-cluster analytics payload yet
- no frontend rendering work
- no hidden fallback to raw ORM serialization

## Acceptance Criteria

- a dedicated social-graph REST endpoint exists
- the endpoint returns explicit API schemas for persons and weighted links
- provider and route boundaries stay explicit
- supported filter semantics are documented and tested
- empty-result behavior is well-defined

## Notes

This task is where the backend contract becomes real for the UI. The most
important quality bar is explicitness: the client should be able to rely on one
clear graph projection shape and one clear definition of supported filters.
