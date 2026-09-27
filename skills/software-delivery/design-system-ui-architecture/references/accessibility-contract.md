# Accessibility Contract

## Table of contents

1. Target and claims
2. Semantics
3. Keyboard
4. Focus
5. Names, labels, and errors
6. Contrast and non-color cues
7. Reflow and scaling
8. Pointer/touch
9. Motion
10. Complex widgets
11. Async feedback
12. Non-text content
13. Handoff obligations

## 1. Target and claims

Inherit the confirmed accessibility target from Stage 01. If no formal target exists, define a validation target as an assumption rather than claiming compliance.

Design documentation may define conformance intent but must not claim formal WCAG conformance without implementation testing and evidence.

## 2. Semantics

Specify expected semantic structure for:

- page title and heading hierarchy;
- landmarks/regions;
- lists;
- tables;
- forms;
- buttons versus links;
- status/alert messages;
- grouped controls.

Do not use visual styling to imply semantics that the implementation cannot represent.

## 3. Keyboard

All required actions should have a keyboard-operable path unless the product is explicitly touch-only and an authoritative accessibility requirement says otherwise.

Define keyboard behavior for menus, dialogs, tabs, disclosures, listboxes/comboboxes, grids, drag/reorder operations, and custom widgets when they exist.

For drag-and-drop tasks, define an alternative non-pointer interaction when the task is essential.

## 4. Focus

Define:

- visible focus treatment;
- logical focus order;
- initial focus for dialogs and task transitions when appropriate;
- focus return after closing overlays;
- focus after validation failure;
- focus after route/screen transition where later implementation needs guidance.

Do not remove visible focus without an equivalent accessible replacement.

## 5. Names, labels, and errors

Controls require persistent accessible names. Define association of:

- label;
- helper/description text;
- required state;
- validation error;
- unit/format hints.

Error messages should identify the problem and correction. Summary error regions may supplement, not replace, field association.

## 6. Contrast and non-color cues

Define contrast target from project NFRs/accepted standard. Ensure status and validation do not rely on color alone. Focus indication must remain distinguishable across relevant backgrounds.

## 7. Reflow and scaling

Design for zoom, text enlargement, and narrow reflow. Avoid layouts that require simultaneous two-dimensional scrolling except where the content itself justifies it, such as large data grids, and provide a deliberate strategy.

## 8. Pointer/touch

Define minimum target expectations according to the accepted accessibility target/platform conventions. Preserve sufficient spacing between adjacent high-risk actions.

## 9. Motion

Respect reduced-motion preferences. Avoid motion that is necessary to understand content. Define alternatives for animated transitions when needed.

## 10. Complex widgets

For custom dialogs, menus, comboboxes, tabs, grids, tree views, carousels, or other complex widgets, Stage 02 should specify expected interaction semantics. Stage 03 should prefer well-tested native/accessible patterns rather than inventing custom behavior.

## 11. Async feedback

Define how users are informed of:

- save success/failure;
- upload progress;
- background completion;
- validation changes;
- dynamically inserted errors;
- loading completion when focus context would otherwise be unclear.

Do not over-announce routine changes.

## 12. Non-text content

For images, icons, charts, maps, or diagrams define whether they are:

- informative and require text alternatives;
- decorative and should be ignored by assistive technology;
- complex and require a data/text alternative.

## 13. Handoff obligations

Stage 03 handoff must preserve:

- target/assumption;
- keyboard contracts;
- focus contracts;
- semantic expectations;
- responsive/reflow expectations;
- error association;
- reduced-motion behavior;
- complex-widget requirements.
