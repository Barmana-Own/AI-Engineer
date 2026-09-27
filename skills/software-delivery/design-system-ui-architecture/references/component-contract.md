# Component Contract

## Table of contents

1. Component-family definition
2. Required specification fields
3. State model
4. Interaction model
5. Form controls
6. Data display
7. Overlays
8. File handling
9. Domain components
10. Composition and anti-patterns

## 1. Component-family definition

A `CMP-*` represents a reusable component family, not a single screen-specific instance. Examples: Button, Text Field, Status Badge, Data Table, File Uploader, Approval Timeline.

## 2. Required specification fields

For each `CMP-*` define:

- Name.
- Purpose.
- Used by screens.
- Anatomy/parts.
- Variants.
- Sizes when applicable.
- Properties/inputs at conceptual level.
- Default state.
- Interactive states.
- Validation/error behavior.
- Loading behavior.
- Disabled/read-only behavior.
- Keyboard behavior.
- Focus behavior.
- Accessible naming/description behavior.
- Content constraints.
- Long-text/overflow behavior.
- Responsive behavior.
- RTL/localization behavior.
- Composition rules.
- Non-goals/misuse cases when important.

Do not define framework props, TypeScript interfaces, CSS classes, or implementation code in Stage 02.

## 3. State model

Applicable components should specify:

- default;
- hover;
- active/pressed;
- focus-visible;
- disabled;
- read-only;
- selected/checked/expanded;
- loading;
- validation error;
- success/confirmed when meaningful;
- unavailable/permission-limited when product policy requires it.

Not every component requires every state. Explicitly omit irrelevant states rather than blindly generating all of them.

## 4. Interaction model

Define:

- click/tap behavior;
- keyboard triggers;
- focus movement;
- dismissal rules;
- escape/cancel behavior;
- outside-click behavior where relevant;
- confirmation requirements;
- asynchronous feedback;
- double-submit prevention expectation;
- disabled-versus-hidden rationale for permission-limited actions.

## 5. Form controls

For fields and selectors define:

- persistent labels;
- placeholder purpose if used;
- helper text;
- required/optional communication;
- formatting/masking expectation;
- validation timing;
- error placement and association;
- character/size limits when product rules require them;
- read-only presentation;
- clear/reset behavior;
- autocomplete/search behavior where relevant.

Do not use placeholder text as the only label.

## 6. Data display

For tables, lists, cards, timelines, and summaries define:

- information hierarchy;
- sorting/filtering/search expectation;
- pagination or progressive loading;
- selection model;
- batch actions;
- row/item actions;
- empty/no-results state;
- loading/skeleton strategy;
- error/retry behavior;
- overflow and truncation;
- mobile transformation;
- numeric/date alignment and localization;
- accessibility strategy for complex grids.

Use a data grid only when interaction requirements justify grid semantics. A visually tabular layout does not automatically require an ARIA grid.

## 7. Overlays

For dialog, drawer, menu, tooltip, popover, and disclosure families define:

- trigger relationship;
- focus entry;
- focus containment when modal;
- dismissal paths;
- escape behavior;
- return-focus behavior;
- background interaction behavior;
- stacking/layering;
- mobile transformation;
- content length limits.

Do not use tooltips for critical information required to complete a task.

## 8. File handling

For upload/attachment components define:

- accepted file intent from product requirements;
- pre-upload validation;
- progress;
- success;
- failure/retry;
- cancellation;
- replacement;
- deletion confirmation;
- preview behavior when relevant;
- multiple-file ordering when relevant;
- accessibility of file status;
- mobile capture/source behavior only when in scope.

Do not invent file size/type limits not established by requirements; mark inferred limits as assumptions.

## 9. Domain components

Create a domain component only when it encapsulates repeated domain behavior or information structure. Link it to `DOM-*`, `BR-*`, `FR-*`, and used `SCR-*` IDs when relevant.

## 10. Composition and anti-patterns

Prefer composition from stable primitives. Do not:

- create `CustomerPageButton`, `InvoicePageCard`, or similar page-specific base components;
- duplicate a component solely because text direction differs;
- create variants for one-off visual preferences;
- overload one component with unrelated responsibilities;
- define behavior that contradicts a screen flow;
- make error handling an afterthought outside the component contract.
