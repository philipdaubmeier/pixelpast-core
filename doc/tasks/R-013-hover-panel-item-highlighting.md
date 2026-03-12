# R-013 - Hover Highlighting Inside Context Panels

## Goal

Extend hover synchronization so that contextual persons and tags are visually marked when a day is hovered.

This makes hover feedback more explicit inside the right-side panels without turning it into persistent selection.

---

## Scope

Implement ephemeral hover-driven highlighting for:

- person items in `PersonsPanel`
- tag items in `TagsPanel`

On hover of a grid cell:

- determine which persons belong to the hovered day
- determine which tags belong to the hovered day
- mark matching person and tag items with a distinct hover visual
- keep the hover highlight separate from persistent selected state

Visual requirements:

- use an outline, ring, glow, or similarly lightweight outer emphasis
- the hover styling must remain visually distinct from persistent active selection styling
- a selected item may also be hover-highlighted at the same time

The matching logic should remain driven by shared state and projection data, not by ad hoc checks inside individual panel rows.

---

## Out of Scope

- no new backend integration
- no persistent state changes
- no URL changes
- no hover-driven selection mutation
- no new filter dimensions
- no day detail view

---

## Acceptance Criteria

- hovering a day visually marks the corresponding persons in `PersonsPanel`
- hovering a day visually marks the corresponding tags in `TagsPanel`
- the hover highlight disappears when the hover ends
- persistent selected items remain selected independently from hover
- an item can show both selected state and hover-highlight state without ambiguity
- hover matching logic is implemented in shared state or projection code, not scattered across panel components

---

## Notes

This task strengthens the hover layer introduced in `R-011`.
Keep the behavior ephemeral and lightweight.
Do not collapse hover styling and persistent selection styling into one visual state.
