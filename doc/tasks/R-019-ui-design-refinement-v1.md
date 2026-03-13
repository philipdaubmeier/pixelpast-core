# R-019 - UI Design Refinement v1

## Goal

Refine the current exploration UI through targeted layout and visual polish only.

This is the first design refinement pass, not a behavioral redesign.

The current UI direction is already strong and should be preserved.
This task is about removing visual friction, tightening spacing, and improving
overall compositional clarity without changing the fundamental interaction
model.

---

## Scope

Apply a focused layout and styling refinement pass across the existing UI.

This task is intentionally limited to design polish.
Do not introduce new interaction patterns, new product concepts, or structural
behavior changes.

### Global Intent

Preserve what already works well, especially the core timeline grid.

The refinement should make the UI feel:

- cleaner
- tighter
- less instructional
- more spatially efficient

### Help Text Removal

Remove instructional helper copy across all relevant subviews.

Examples include text such as:

- `Hover a day to preview its people, or pin people as durable filters.`

Apply the same principle consistently to similar helper text throughout the UI.

The current interface should stand on its own without inline instructional
sentences.
If onboarding is needed later, it should be handled through a dedicated tour or
guide rather than persistent helper text in the main layout.

### Section Eyebrow Removal

Remove the small category or eyebrow labels that sit above the actual section
headings.

Examples include labels such as:

- `Context`
- `Timeline Grid`

Keep the actual main headings where they remain useful, but remove the extra
pre-heading label layer.

### Timeline Grid Year Labels

Adjust the rotated year labels in the timeline grid so that they are:

- larger
- visually stronger
- positioned closer to the grid

The labels should feel more integrated with the year blocks rather than floating
too far away from them.

### Timeline Grid Preservation

Do not redesign the timeline grid itself.

The grid view is considered correct as it is and should remain visually and
structurally unchanged.

Allowed refinement:

- reduce the vertical spacing between consecutive year blocks

Target direction:

- the gap between years should be tightened to roughly the height of one grid
  square

No other substantive grid styling changes should be introduced in this task.

### Top Bar Refinement

Make the top bar significantly slimmer.

Target direction:

- remove all headlines, replace by pixelpast logo (can be found as svg file in doc/img folder), scaled down to not take up too much space
- a rectangular bar
- no rounded outer corners
- flush to the top edge of the browser viewport
- flush to the left and right edges of the browser viewport
- tighter internal spacing

Also remove the placeholder region for search and future controls from the top
bar.

### Persons View Simplification

Simplify the persons panel so that it shows only the person names.

Remove the secondary detail area beneath the names that currently shows
additional per-person information.

### Tags View Simplification

Apply the same simplification to the tags panel.

Show only the tags themselves.
Remove the secondary list or detail presentation that currently exposes tag
paths and related detail content.

### Scroll and Panel Layout Refinement

Remove the global page scrollbar.

The intended layout is:

- the top bar remains fixed at the top of the browser view
- the main grid region fills the space from the top bar down to the bottom edge
  of the browser viewport
- the grid region has its own local scrollbar
- the three right-side context panels divide the available vertical space into
  thirds
- if content exceeds available space, each of those panels scrolls internally

The overall browser viewport should feel fully occupied by the application
layout without requiring page-level scrolling.

### Chip and Button Density

Reduce the visual bulk of rounded filter chips and similar buttons used for
filters, tags, persons, and related UI elements.

Adjustments should include:

- smaller overall control size
- noticeably reduced internal padding
- tighter spacing between text and chip boundaries
- slightly smaller text where helpful

The goal is denser, more precise controls without making them feel cramped or
hard to scan.

---

## Out of Scope

- no behavior changes
- no interaction model changes
- no new onboarding flow, guide, or product tour
- no redesign of the timeline grid cell system
- no changes to hover semantics
- no changes to persistent filter semantics
- no changes to API contracts or data flow
- no new controls in the top bar
- no new panel content types
- no accessibility or keyboard interaction redesign in this task unless required
  as a direct consequence of the layout-only changes

---

## Acceptance Criteria

- helper and instructional text is removed across the relevant subviews
- eyebrow labels above main section headings are removed
- rotated year labels are larger and positioned closer to their grids
- the timeline grid itself remains unchanged apart from tighter spacing between
  year blocks
- the top bar is slimmer, rectangular, and flush with the browser edges
- the top bar no longer contains placeholder search or future-control space
- the persons panel shows only person names
- the tags panel shows only tags
- the application no longer uses a global page scrollbar
- the grid region scrolls locally within the viewport
- the three right-side context panels divide the available height evenly and
  scroll internally when needed
- rounded chips and similar filter controls are visually smaller and denser

---

## Notes

This task should be treated as a refinement pass, not a reinvention pass.

Preserve the current strengths of the interface.
Prefer subtraction over addition.
Prefer spacing, density, and proportion adjustments over new visual concepts.

If a proposed change starts to alter behavior or the overall mental model of the
exploration surface, it is out of scope for this task.
