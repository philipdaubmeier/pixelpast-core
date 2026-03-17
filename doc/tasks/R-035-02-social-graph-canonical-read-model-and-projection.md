# R-035-02 - Social Graph Canonical Read Model and Projection

## Goal

Define the backend read model for the social graph directly from canonical
person and asset relationships.

The first social-graph increment should not introduce a derived social-graph
table. It should read canonical data and compute the graph projection on the
read path.

## Dependencies

- `R-003`
- `R-024-01`

## Scope

### Canonical Read Direction

Add a repository-facing read path that derives a person co-occurrence graph
from canonical tables.

The primary inputs are:

- `person`
- `asset_person`

If required for deterministic filtering or qualification of eligible rows, the
read path may also join canonical `asset`. That is still considered canonical
read behavior, not a derived-model dependency.

`event_person` is explicitly out of scope for this first increment.

### Projection Contract Direction

Define an explicit API-facing projection shape for the graph.

Suggested response shape:

```json
{
  "persons": [
    { "id": "p_1", "name": "Anna", "occurrence_count": 42 }
  ],
  "links": [
    { "person_ids": ["p_1", "p_2"], "weight": 17 }
  ]
}
```

Expected semantics:

- one person entry per qualifying canonical person
- `occurrence_count` describes how often that person appears on qualifying
  assets
- one link entry per unordered person pair
- `weight` counts how many qualifying assets contain both persons

Ordering should be deterministic so the response is stable for tests and UI
diffing.

### Repository Rules

The repository should make the graph-building steps explicit:

- load qualifying person-asset memberships
- count per-person occurrences
- count per-pair co-occurrences
- return a stable projection DTO or repository snapshot

Do not hide these responsibilities inside a generic helper or a connector.

## Out of Scope

- no REST route yet
- no UI transport yet
- no persisted cluster analytics
- no stored layout coordinates
- no weighting heuristics beyond raw co-occurrence counts
- no `event_person`

## Acceptance Criteria

- there is an explicit backend read path for social-graph person and pair data
- the projection contains person ids and weighted person-pair tuples
- pair counting is deterministic and treats links as unordered pairs
- per-person occurrence counts are available for UI node sizing
- tests cover isolated qualifying persons, repeated co-occurrence, and stable
  pair counting

## Notes

This task is intentionally canonical-read-only. That is architecturally
acceptable here because the projection is graph-oriented rather than day-
aggregate-oriented.
