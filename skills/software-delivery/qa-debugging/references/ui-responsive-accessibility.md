# UI, Responsive, RTL, and Accessibility QA

## Table of contents

1. Scope
2. Viewport strategy
3. Layout and overflow
4. Forms and controls
5. Navigation and overlays
6. Tables and dense data
7. RTL/LTR and bidirectional content
8. Keyboard accessibility
9. Focus management
10. Semantics and labels
11. Errors and status messages
12. Contrast and non-color cues
13. Zoom, text resizing, and reflow
14. Motion and animation
15. Touch and pointer behavior
16. Accessibility standard and limitations
17. Exit criteria

## 1. Scope

Treat UI quality as functional correctness where users can be blocked, misled, or unable to operate the product. Use WCAG 2.2 AA as the default accessibility reference unless the project explicitly defines another applicable standard.

Do not claim formal WCAG conformance unless the project has undergone the required level of evaluation. Stage 10 performs release-oriented accessibility verification.

## 2. Viewport strategy

Use actual project breakpoints when defined in CSS/Tailwind/theme/configuration. Do not invent device-specific support claims.

At minimum test representative classes for critical flows:

- narrow mobile;
- normal mobile;
- tablet/small laptop when layouts reflow there;
- desktop;
- wide layout for dashboards/tables when relevant.

Test breakpoint edges where layout logic changes, not only comfortable midpoint widths.

## 3. Layout and overflow

Check every critical screen for:

- horizontal overflow;
- clipped content;
- overlapping text/buttons;
- off-screen actions;
- fixed/sticky header collisions;
- sidebars trapping content;
- footer overlap;
- viewport-height assumptions;
- safe area issues on mobile-like layouts where relevant;
- long labels/URLs/names;
- validation text expansion;
- empty and loading states;
- localized text expansion.

A page that technically renders but hides the primary action is a functional defect.

## 4. Forms and controls

Verify:

- labels are visible or programmatically associated;
- placeholder is not the only label for important fields;
- required state is understandable;
- disabled vs readonly state is correct;
- field errors are associated with the field;
- keyboard can reach custom controls;
- date/select/autocomplete controls are usable without pointer-only assumptions;
- mobile keyboards/input modes are sensible where inspectable;
- submit state prevents unsafe duplicate operations;
- long values do not destroy layout.

## 5. Navigation and overlays

For menus, drawers, dialogs, modals, popovers, tooltips, and command palettes:

- opening control is reachable;
- focus moves into modal/dialog where appropriate;
- keyboard interaction works;
- Escape closes when expected;
- background does not remain interactable if modality requires isolation;
- focus returns to a sensible trigger after close;
- scroll locking does not strand the page;
- overlay remains within viewport;
- overlay is not clipped by stacking context;
- screen reader semantics/labels are present when inspectable.

## 6. Tables and dense data

Check:

- narrow layouts have an intentional strategy: scroll, stacking, priority columns, or responsive alternative;
- headers remain understandable;
- action menus remain reachable;
- pagination/filter/sort controls do not overflow;
- long cells wrap/truncate with accessible detail where needed;
- horizontal scroll does not hide essential context without a usable alternative;
- keyboard focus remains visible inside scroll containers.

## 7. RTL/LTR and bidirectional content

For Persian/Arabic or RTL products test:

- document direction and component direction;
- icons whose meaning depends on direction;
- breadcrumb/stepper ordering;
- form alignment;
- tables and pagination;
- drawers/sidebar origin;
- carousel/navigation arrows;
- phone/email/URL/identifier display;
- mixed Persian/Latin text;
- numbers, dates, currency, punctuation;
- code/token fields that should remain LTR;
- modal alignment and toast placement;
- scrollbars and fixed-position elements.

Do not globally mirror components whose semantic direction should remain LTR.

## 8. Keyboard accessibility

For critical journeys, complete the path without a mouse where feasible.

Verify:

- logical tab order;
- all actionable controls reachable;
- no keyboard trap;
- buttons activate with expected keys;
- links behave as links;
- custom widgets expose usable keyboard behavior;
- skip/navigation mechanisms exist where project complexity warrants them;
- hidden controls are not accidentally tabbable.

## 9. Focus management

Check:

- focus indicator is visible;
- focus is not lost after route/state updates;
- invalid form submission moves or guides focus appropriately;
- modal open/close manages focus;
- dynamically inserted critical content is reachable;
- destructive confirmation does not put default focus on an unsafe action without rationale.

## 10. Semantics and labels

Inspect critical screens for:

- one coherent page heading structure;
- landmark/region semantics where appropriate;
- real buttons for actions and links for navigation unless custom semantics are justified;
- accessible names for icon-only controls;
- form associations;
- table semantics for real tabular data;
- images/icons with meaningful alternative treatment;
- decorative content hidden from assistive semantics when appropriate.

## 11. Errors and status messages

Verify errors are:

- specific enough to recover;
- not color-only;
- associated with relevant field/context;
- not replaced by raw backend errors;
- persistent long enough to understand;
- announced or semantically discoverable for important dynamic status changes where implementation supports it.

## 12. Contrast and non-color cues

Where measurement tools are available, evaluate critical text and interactive states against WCAG 2.2 AA contrast requirements. If no measurement is available, do not assert numeric compliance; flag obvious low-contrast risks for verification.

Check that error/success/selected/disabled states do not rely solely on color where users need another cue.

## 13. Zoom, text resizing, and reflow

For critical pages, test practical browser zoom/text enlargement where possible. Look for:

- hidden controls;
- clipped text;
- broken fixed-height containers;
- overlapping dialogs;
- unusable horizontal scrolling;
- loss of content or functionality.

## 14. Motion and animation

Check:

- animation does not block interaction;
- loading animations terminate;
- reduced-motion preference is respected where significant motion exists or project requirements demand it;
- scroll animation does not make essential content inaccessible;
- motion does not hide state changes.

## 15. Touch and pointer behavior

For mobile-oriented flows:

- important targets are not impractically small or crowded;
- hover-only behavior has a touch alternative;
- drag-only operations have an accessible alternative when required;
- fixed bottom actions are not covered by browser/UI chrome assumptions;
- touch interactions do not accidentally trigger adjacent destructive controls.

## 16. Accessibility standard and limitations

Use WCAG 2.2 AA as a reference baseline unless overridden by project/legal requirements. Distinguish:

- automated accessibility scan findings;
- keyboard/manual findings;
- semantic inspection findings;
- visual contrast findings;
- areas not evaluated.

Automated scans do not prove accessibility conformance.

## 17. Exit criteria

Before PASS for a UI product:

- critical flows are usable at required viewport classes;
- no release-blocking overflow/clipping exists;
- critical flows are keyboard operable to the practical extent required;
- no known P0/P1 accessibility defect blocks a core flow;
- RTL/LTR critical layouts behave correctly where applicable;
- remaining accessibility findings are documented honestly;
- unsupported/unverified browser/device claims are not made.
