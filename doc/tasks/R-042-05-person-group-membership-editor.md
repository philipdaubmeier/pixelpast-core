# R-042-05 - Person Group Membership Editor

## Goal

Implement the dedicated membership-management subview for one `PersonGroup`,
including the API path for loading and replacing that group's members.

## Dependencies

- `R-042-01`
- `R-042-02`
- `R-042-04`

## Scope

### Add Group-Membership Load and Save Contracts

Introduce explicit manage-data endpoints for one group's membership surface.

The backend should support:

- loading the current persisted members for one group
- replacing that group's members through one batch save payload

The membership save contract should treat the submitted member list as the next
authoritative membership set for that group.

### Add a Dedicated Membership Subview

When the user activates the per-row membership-edit action from `Person
Groups`, open a dedicated group-focused subview inside the overlay.

The subview should clearly show:

- the current group being edited
- the current persisted or drafted member list
- the add-member control
- the remove-member controls

Do not push this workflow into a tiny popover or inline table expansion.

### Add Persisted-Person Search and Add Flow

Provide a person search input with suggestion dropdown behavior for adding
members.

Behavior:

- the source catalog should be persisted persons only
- typing filters candidate persons
- selecting a suggestion or pressing enter on a valid match adds that person to
  the local membership draft
- duplicate additions should be prevented

This task must not create new persons from inside the membership editor.

### Support Explicit Member Removal

Render the current members in a removable list.

The user should be able to:

- remove one member from the draft through an explicit action
- review the resulting membership set before saving

### Save, Discard, and Reload the Membership Draft

The membership subview should follow the same explicit draft rules as the other
manage-data sections.

Required behavior:

- apply saves the membership replacement and keeps the subview open
- save-and-close saves and leaves the overlay
- discard restores the last loaded persisted membership set
- after a successful save, the membership subview reloads from the API

The parent `Person Groups` catalog should also remain consistent with saved
member counts after returning.

## Out of Scope

- no creation of new persons from the membership editor
- no use of unsaved person drafts from the persons section
- no bulk editing of multiple groups at once

## Acceptance Criteria

- a dedicated manage-data membership contract exists for one person group
- the membership editor loads one group's persisted members on entry
- the editor supports adding members through a persisted-person search picker
- the editor supports removing members from the local draft
- duplicate member additions are prevented
- membership saves are batch replacements of the group's member set
- successful saves reload persisted membership state and keep group counts
  coherent when returning to the catalog

## Notes

This task should keep the mental model simple:

- one group in focus
- one explicit member draft
- one replacement save
