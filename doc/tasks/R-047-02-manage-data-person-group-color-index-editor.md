# R-047-02 - Manage-Data Person-Group Color-Index Editor

## Goal

Add explicit `color_index` editing to the `Person Groups` manage-data editor.

## Dependencies

- `R-042-04`
- `R-047-01`

## Scope

### Add A Palette-Backed Group Color Picker

The `Person Groups` section should expose a compact color-selection control for
each group.

The control should:

- present a curated list of palette slots
- show the currently selected slot clearly
- allow clearing the selection back to `no color`

The UI should not ask the user to type numeric values manually.

### Keep The Stored Value Numeric

The client may render a swatch for each option, but the drafted and persisted
value remains the numeric `color_index`.

The UI owns the current palette mapping for those indices.

### Preserve Existing Draft And Save Semantics

Editing group color must follow the existing manage-data rules:

- edits stay local until the section is saved
- discard restores the last loaded persisted state
- successful save reloads the section

### Make Missing Color Assignments Explicit

A group without `color_index` should render as intentionally unassigned rather
than as a broken or invisible value.

Examples:

- neutral outlined swatch
- `No color` label

## Out of Scope

- no theme switcher
- no custom hex picker
- no automatic color assignment algorithm in this task

## Acceptance Criteria

- the `Person Groups` editor lets the user choose or clear a `color_index`
- the draft model preserves `color_index` locally until save
- saved groups reload with the persisted `color_index`
- unassigned groups are visually distinguishable from assigned groups

## Notes

This editor should stay simple and fast.
It is a palette-slot picker, not a design tool.
