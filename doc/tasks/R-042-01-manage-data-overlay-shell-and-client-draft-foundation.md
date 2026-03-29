# R-042-01 - Manage Data Overlay Shell and Client Draft Foundation

## Goal

Introduce the shared UI shell and client-side editing foundation for the new
`Manage Data` workspace overlay.

This task should establish the structural runtime for all later manage-data
sections without yet committing to entity-specific table details beyond what is
needed for a reusable editing pattern.

## Dependencies

- `R-035`

## Scope

### Add a Subdued Top-Bar Manage Action

Extend the app shell with a `Manage` action placed at the far right of the top
bar.

The control should:

- read as secondary shell chrome rather than a new main-view tab
- remain visually quieter than primary exploration navigation
- open and close the manage-data workspace overlay

The open/closed state should remain local app-shell UI state, not URL
state.

### Introduce the Workspace Overlay Shell

Add a full-screen overlay dedicated to manage-data workflows.

The overlay should provide:

- a close affordance
- a left-side section list
- a right-side content frame for the active editor
- a persistent action region for discard, apply, and save-and-close behavior
- a clear dirty-state indicator

The overlay should behave as a temporary workspace layered above the
exploration UI, not as a long-lived app mode.

### Add Shared Section Runtime and Dirty-State Rules

Create a shared section runtime that can:

- load section data when a section becomes active
- store a local editable draft for the active section
- detect whether the draft differs from the last loaded persisted snapshot
- coordinate discard, apply, and save-and-close actions

To keep the first version bounded, section switching with unsaved edits should
use an explicit guard flow:

- stay in the current section
- discard changes and switch
- save changes and switch

Do not silently preserve hidden unsaved drafts for multiple sections at once in
this task.

### Introduce Reusable Catalog-Editor Primitives

Create shared manage-data UI primitives suitable for the `Persons` and `Person
Groups` editors.

The reusable foundation should cover:

- section header layout
- quick-search input pattern
- editable table layout
- add-row affordance
- inline text editing controls
- empty-state and loading-state framing
- error-state framing

The goal is not a generic admin framework, but a small explicit foundation that
keeps the first manage-data sections visually and behaviorally consistent.

## Out of Scope

- no entity-specific persistence contracts
- no person-specific alias semantics beyond shared field-edit affordances
- no person-group membership editor
- no URL persistence for overlay state
- no generic reusable modal framework for the entire app

## Acceptance Criteria

- the top bar exposes a subdued `Manage` action at the far right
- clicking the action opens a full-screen manage-data overlay
- the overlay exposes section navigation and a content region
- the overlay supports close, discard, apply, and save-and-close actions
- active-section drafts are tracked locally and marked dirty when changed
- switching away from a dirty section requires an explicit decision
- shared catalog-editor primitives exist and are usable by later person and
  group editors

## Notes

This task should solve workspace shell and draft lifecycle concerns once so the
entity-specific tasks can stay focused on their catalogs.
