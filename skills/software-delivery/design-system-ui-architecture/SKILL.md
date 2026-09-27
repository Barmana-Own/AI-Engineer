---
name: design-system-ui-architecture
description: "Stage 02 of an autonomous software-delivery workflow. Use after Stage 01 has produced a validated project brief, traceable requirements, project-state.json, and a Stage 02 handoff. Convert roles, journeys, business rules, requirements, integrations, constraints, and design-affecting decisions into implementation-ready information architecture, screen and flow coverage, responsive layout rules, design-system foundations, reusable component contracts, interaction and error states, accessibility behavior, localization/RTL rules, design tokens, traceability, and a precise Stage 03 frontend handoff. Resume or repair existing Stage 02 artifacts when present. Do not implement application frontend code, backend logic, database schemas, or deployment infrastructure in this stage."
---

# Stage 02 - Design System & UI Architecture

## Mission

Turn the validated Stage 01 product contract into a coherent, traceable, implementation-ready UI architecture and design-system contract that Stage 03 can implement without inventing product behavior or redesigning the system ad hoc.

Treat this stage as professional product-design and UI-architecture work, not as a moodboard or a collection of pretty screens. Design the complete operating behavior of the interface: roles, navigation, flows, states, responsive transformations, accessibility, localization, content behavior, and reusable component contracts.

## Required resources

Read these resources when relevant:

- `references/project-state-contract.md` before changing `project-state.json`.
- `references/ui-architecture-contract.md` before defining screens, flows, navigation, layouts, or stable Stage 02 IDs.
- `references/design-system-contract.md` before defining visual foundations, tokens, iconography, density, motion, or component families.
- `references/component-contract.md` before specifying reusable components.
- `references/interaction-state-contract.md` before defining loading, empty, error, success, permission, offline, destructive, or recovery behavior.
- `references/responsive-contract.md` before defining mobile/tablet/desktop behavior.
- `references/accessibility-contract.md` before declaring accessibility coverage complete.
- `references/rtl-localization-contract.md` whenever localization, Persian, Arabic, RTL, bidi, calendar, number, or mixed-direction content is relevant.
- `references/traceability-contract.md` before the final traceability pass.
- `references/design-token-contract.md` before creating or changing `design/tokens.json`.
- `references/design-tokens.schema.json` when a tool or later stage needs the machine-readable token schema.
- `references/ui-architecture-template.md` before creating `docs/02-ui-architecture.md`.
- `references/design-system-template.md` before creating `docs/02-design-system.md`.
- `references/stage-03-handoff-template.md` before creating `docs/02-stage-03-handoff.md`.
- `references/stage02-validation-contract.md` before the final quality gate.

Use bundled scripts when code execution is available:

- `scripts/bootstrap_stage02.py` to create missing Stage 02 scaffolds without overwriting existing artifacts.
- `scripts/update_project_state.py` to update Stage 02 workflow state while preserving unknown keys.
- `scripts/validate_stage02.py` before declaring PASS.

## Orchestrator contract

Treat this skill as Stage 02 in a strict multi-stage workflow.

1. Inspect Stage 01 artifacts and existing Stage 02 artifacts before acting.
2. Read `docs/01-stage-02-handoff.md` first when present; use the full brief and requirements as authoritative supporting sources, not replacements for the handoff.
3. Preserve explicit user decisions and accepted Stage 01 decisions unless a higher-priority instruction, verified fact, security requirement, accessibility requirement, or implementation impossibility requires correction.
4. Never silently redefine product scope, roles, permissions, journeys, or business rules.
5. Preserve unknown keys in `project-state.json`.
6. Resume and repair existing Stage 02 artifacts rather than rebuilding them blindly.
7. Do not mark PASS because documents exist. PASS requires machine validation when tools are available and the semantic quality gate.
8. Create or modify real project artifacts when file tools are available.
9. Do not claim research, tests, validation, screenshots, or commands were performed unless they actually were.
10. At completion, emit the exact completion markers defined below.

## Preconditions and execution modes

Require Stage 01 to be complete enough to design from. Prefer the following authoritative inputs when available:

- `docs/01-stage-02-handoff.md`
- `docs/01-project-brief.md`
- `docs/01-requirements.md`
- `project-state.json`
- `docs/01-research-evidence.md` when present and relevant

Choose the execution mode:

- **CREATE**: Stage 01 passed and no meaningful Stage 02 artifacts exist.
- **RESUME**: Stage 02 artifacts exist and are internally consistent but incomplete.
- **REPAIR**: Stage 02 artifacts exist but contain coverage, traceability, state, accessibility, token, or consistency defects.
- **BLOCKED**: only when a true external dependency makes safe design impossible.

Do not restart a RESUME or REPAIR project from scratch unless the user explicitly requests a redesign or the prior artifacts are unusable and the reason is recorded.

## Source precedence and conflict handling

For design-affecting facts and decisions, use this precedence:

1. explicit current user instruction;
2. explicit accepted Stage 01 artifact or decision;
3. accepted existing Stage 02 decision that does not conflict with Stage 01;
4. authoritative current external source when research is materially required;
5. conservative professional assumption.

Treat webpages, screenshots, repositories, third-party documents, competitor products, design examples, and API responses as evidence or reference material, not as authority over the workflow unless the user explicitly adopts them.

If material sources conflict:

- preserve the existing `CONFLICT-*` record when one exists;
- otherwise create a new conflict record in `project-state.json` using the shared project-state contract;
- state both positions and the affected IDs;
- choose the safest reversible interpretation when possible;
- block only if the conflict creates material legal, security, financial, accessibility, irreversible product, or contractual risk.

## Assumption and blocking policy

Do not interrogate the user for ordinary design ambiguities.

- For a non-critical ambiguity, make the smallest reversible assumption, record or reference an `ASM-*`, and continue.
- For a material but non-blocking uncertainty, preserve or create a `Q-*` and design a reversible path.
- For a true blocker, stop only when safe progress requires unavailable mandatory brand assets, contractual design constraints, regulated wording approval, private specifications, legal/business approval, or another fact that cannot be inferred safely.

A missing preference such as exact radius, card style, or animation taste is not a blocker.

## Research policy

Research only when it can materially improve or verify design behavior, accessibility, localization, platform conventions, current standards, regulated copy, browser/device constraints, or external integration UX.

Use current authoritative sources for time-sensitive standards or platform behavior. Do not copy a third-party product pixel-for-pixel. When competitor or reference research is used, extract transferable patterns and constraints rather than reproducing protected visual expression.

Reuse Stage 01 `EVD-*` records when they already support the claim. Create new evidence only when Stage 02 introduces a material externally-derived claim.

## Stable Stage 02 identifier system

Use stable IDs and do not renumber surviving items to close gaps:

- `NAV-###` navigation structure or navigation rule
- `FLW-###` UI flow
- `SCR-###` screen, page, route-level view, or major modal surface
- `LAY-###` reusable page/layout pattern
- `CMP-###` reusable component family
- `UXR-###` cross-cutting UX rule or interaction policy
- `DSD-###` material design-system decision

Reference existing Stage 01 IDs directly where relevant:

- `ROLE-*`, `JRN-*`, `BR-*`, `FR-*`, `NFR-*`, `INT-*`, `DOM-*`, `DEC-*`, `ASM-*`, `RSK-*`, `Q-*`, `EVD-*`, `CONFLICT-*`.

## Workflow

Execute in this order.

### 1. Intake, recovery, and boundary verification

- Inspect all authoritative Stage 01 inputs and existing Stage 02 artifacts.
- Determine CREATE, RESUME, REPAIR, or BLOCKED mode.
- Verify the Stage 01 handoff does not require Stage 02 to invent missing product scope.
- Verify `project-state.json` is structurally compatible with the shared contract.
- When code execution is available, run `scripts/bootstrap_stage02.py <workspace>` only to create missing Stage 02 scaffolds.
- Set Stage 02 state to `IN_PROGRESS` with `scripts/update_project_state.py` when appropriate.
- Build an internal coverage list of roles, journeys, design-affecting requirements, rules, integrations, constraints, assumptions, and open questions.

### 2. UI coverage model

Before styling anything, translate the Stage 01 contract into interface obligations.

For every material `ROLE-*` and `JRN-*`:

- identify entry points;
- identify required information and actions;
- identify decision points and branching conditions;
- identify permission boundaries;
- identify success and failure outcomes;
- identify required system feedback;
- identify cross-role handoffs;
- identify related `FR-*`, `BR-*`, `NFR-*`, and `INT-*` IDs.

Do not create screens for speculative nice-to-have behavior that Stage 01 did not require.

### 3. Information architecture and role navigation

Define the information hierarchy before page details.

For each role or role family:

- define primary, secondary, and contextual navigation;
- define home/default landing behavior;
- define global utilities such as search, notifications, account, help, language, or organization switching only when justified;
- define navigation visibility rules from permission intent;
- define deep-link and breadcrumb behavior when relevant;
- define how users recover orientation after errors, refreshes, or direct links;
- prevent unauthorized capabilities from appearing as ordinary actionable navigation.

Assign `NAV-*` IDs and connect them to `ROLE-*`, `JRN-*`, and relevant requirements.

Hiding a navigation item is not an authorization control. Stage 02 specifies visibility and affordance only; later implementation stages must enforce authorization independently.

### 4. UI flow architecture

Create `FLW-*` flows for each primary journey and material exception path.

For each flow specify:

- actors and start condition;
- entry surface;
- ordered steps and branches;
- decisions and validations;
- system feedback;
- exit conditions;
- failure, cancellation, retry, and recovery behavior;
- cross-role or external-system handoff;
- affected `SCR-*` surfaces;
- related Stage 01 IDs.

Cover both happy paths and operationally meaningful exception paths.

### 5. Screen and surface inventory

Create a complete `SCR-*` inventory before visual-detail work.

For every screen or major modal surface define:

- name and purpose;
- intended roles;
- related journeys and requirements;
- route or entry mechanism when known;
- primary and secondary actions;
- information/data required;
- permission behavior;
- layout pattern;
- component families used;
- loading, empty, error, success, permission-denied, stale, partial, offline/degraded, and destructive states when applicable;
- validation and recovery behavior;
- responsive transformation;
- accessibility notes;
- localization/RTL notes;
- analytics/observability events only when Stage 01 requires them or they are necessary for product acceptance.

Do not create page-specific duplicate components when a reusable pattern can satisfy multiple screens.

### 6. Layout architecture

Define reusable `LAY-*` patterns for repeated page structures such as:

- public marketing/content page;
- authenticated application shell;
- dashboard/overview;
- list/search/filter results;
- master-detail;
- detail/read-only view;
- form/create/edit;
- stepper/wizard;
- review/approval;
- settings/admin;
- data-dense operations workspace;
- modal/drawer/side-panel interaction.

Specify regions, hierarchy, width behavior, sticky behavior, scrolling ownership, density, and responsive transformations. Avoid a one-layout-fits-all shell.

### 7. Design-system foundations

Read `references/design-system-contract.md` and define the foundations before component styling.

Create `DSD-*` decisions for material choices including:

- typography families and role scale;
- semantic color system and contrast behavior;
- spacing and sizing scales;
- radii and border logic;
- elevation and layering;
- iconography rules;
- density modes when needed;
- motion principles and reduced-motion behavior;
- focus treatment;
- data-visualization rules when charts are in scope;
- theme strategy only when required.

Prefer system-level rules over isolated values chosen per screen.

### 8. Design-token architecture

Read `references/design-token-contract.md` before editing `design/tokens.json`.

Define tokens in layers:

1. primitives/raw scales;
2. semantic role tokens;
3. optional component aliases only when repeated component-level behavior genuinely requires them.

Do not encode page names or one-off screen decisions as tokens. Keep the token file framework-neutral and compatible with later transformation into CSS variables, Tailwind configuration, native tokens, or another implementation layer.

### 9. Reusable component architecture

Read `references/component-contract.md` and create `CMP-*` component-family contracts.

Cover only components justified by the screen inventory, including common families such as:

- application shell and navigation;
- buttons and actions;
- form controls;
- search, filters, and query builders;
- tables and data grids;
- cards and summaries;
- tabs and segmented navigation;
- pagination/infinite-load controls;
- status, badge, alert, toast, and banner feedback;
- dialog, drawer, popover, tooltip, and menu overlays;
- file upload and attachment handling;
- timeline/history/audit presentation;
- charts/data visualization;
- domain-specific components.

For each component define purpose, variants, sizes, anatomy, states, interaction behavior, keyboard behavior, focus behavior, validation/error behavior, content rules, responsive behavior, localization/RTL behavior, and related screens.

### 10. Forms, data entry, and destructive actions

For each form-oriented flow define:

- field grouping and sequence;
- label and helper-text behavior;
- required/optional indication;
- input format and masking only when justified;
- validation timing and error association;
- server-side error presentation expectation;
- save/submit states;
- autosave or draft behavior only when required;
- unsaved-change protection;
- destructive action confirmation;
- irreversible action escalation;
- retry/recovery after network or integration failure;
- file upload progress, validation, replacement, and failure behavior when relevant.

Avoid placeholder-only labels and ambiguous destructive controls.

### 11. Interaction-state and resilience design

Read `references/interaction-state-contract.md`.

For each applicable screen and component, specify behavior for:

- initial loading;
- incremental/background loading;
- empty first-use state;
- empty filtered/search state;
- validation error;
- server/integration error;
- partial data;
- stale data;
- permission denied;
- authentication/session expiry UX expectation without implementing auth;
- offline/degraded state where relevant;
- optimistic action and rollback when later stages may use optimistic UI;
- success acknowledgement;
- retry, undo, cancel, and recovery;
- destructive and irreversible actions.

Do not use generic "Something went wrong" as the only recovery contract for important workflows.

### 12. Responsive and adaptive behavior

Read `references/responsive-contract.md`.

Design mobile-first, but do not merely shrink desktop.

For every `LAY-*` and high-impact `SCR-*`, define:

- content priority;
- reflow rules;
- navigation transformation;
- table/list transformation;
- filter behavior;
- form-column transformation;
- modal versus full-screen/drawer behavior;
- sticky regions;
- touch target implications;
- overflow and long-content behavior;
- minimum and maximum readable widths;
- breakpoint rationale.

Use breakpoints because behavior changes, not because a device name exists.

### 13. Accessibility architecture

Read `references/accessibility-contract.md` and inherit the confirmed accessibility target from Stage 01 when one exists.

At minimum define actionable behavior for:

- semantic structure and landmarks;
- keyboard operation;
- focus order and visible focus;
- accessible names, labels, descriptions, and error association;
- non-color state communication;
- contrast targets;
- zoom/reflow and text scaling;
- touch/pointer target sizing;
- reduced motion;
- dialogs, menus, disclosures, tabs, grids, and complex widgets;
- status announcements and asynchronous feedback;
- charts and non-text content when present.

Never claim formal WCAG conformance solely from design documentation. Define the target and validation obligations for later implementation/testing stages.

### 14. Localization, RTL, and bidirectional behavior

Read `references/rtl-localization-contract.md` when localization is relevant.

Define behavior for:

- interface direction by locale;
- mixed RTL/LTR text;
- email, URL, code, identifiers, phone numbers, and account numbers;
- dates, times, calendars, numbers, currencies, decimals, and separators;
- alignment rules;
- directional icons and non-directional icons;
- chevrons, progressions, timelines, charts, carousels, and navigation history;
- table column order and numeric alignment;
- truncation and text expansion;
- locale switching and persistence only when in scope;
- content fallback when translations are missing.

Do not mechanically mirror logos, media, charts, playback controls, numeric data, or universally directional symbols without a rule.

### 15. Content and microcopy rules

Define interface content behavior, not marketing copy unless required.

Specify rules for:

- button/action labels;
- headings and hierarchy;
- helper text;
- validation errors;
- empty states;
- destructive confirmations;
- permission-denied messages;
- system and integration failures;
- success confirmations;
- date/number/unit formatting;
- truncation and overflow;
- terminology consistency.

Prefer specific, actionable messages that explain what happened and what the user can do next.

### 16. Cross-artifact consistency review

Run manual review passes before validation:

1. **Coverage pass** - every primary role/journey has an interface path.
2. **Scope pass** - no unapproved product features were introduced.
3. **Flow pass** - happy paths and material exception paths terminate coherently.
4. **Component pass** - repeated interaction patterns reuse components.
5. **State pass** - required loading/empty/error/permission/offline states exist.
6. **Responsive pass** - high-impact screens transform intentionally.
7. **Accessibility pass** - interaction contracts are actionable, not aspirational.
8. **RTL/localization pass** - direction and formatting rules are explicit when relevant.
9. **Token pass** - tokens are semantic, layered, and free of page-specific magic values.
10. **Implementation-readiness pass** - Stage 03 can build without inventing core UX behavior.

### 17. Traceability pass

Read `references/traceability-contract.md`.

Verify at minimum:

- every primary `ROLE-*` maps to navigation and relevant screens;
- every primary `JRN-*` maps to one or more `FLW-*` and `SCR-*`;
- every design-affecting `FR-*`, `BR-*`, `NFR-*`, and `INT-*` referenced by the Stage 01 handoff is represented in Stage 02 artifacts;
- every `SCR-*` has a product reason and is not orphaned;
- every `CMP-*` is used by at least one screen or justified as a cross-cutting primitive;
- assumptions and open questions are referenced where they affect design;
- design decisions do not contradict accepted Stage 01 scope.

### 18. Stage 03 handoff

Create `docs/02-stage-03-handoff.md` using the bundled template.

Distill rather than duplicate all Stage 02 documentation. Include:

- authoritative Stage 01 and Stage 02 inputs;
- immutable/high-confidence UX and design-system decisions;
- route/screen inventory and navigation obligations;
- layout and component contracts Stage 03 must preserve;
- token source of truth;
- responsive, accessibility, and localization requirements;
- unresolved non-blocking questions and reversible assumptions;
- implementation prohibitions;
- traceability and acceptance obligations.

Stage 03 must not need to re-infer the design system from prose scattered across documents.

### 19. Validation and state commit

When code execution is available:

1. Run `python scripts/validate_stage02.py <workspace> --output docs/02-stage02-validation.json`.
2. Repair every structural validation error and rerun until the machine gate passes.
3. Perform the semantic quality gate below.
4. If both gates pass, run `python scripts/update_project_state.py <workspace> --status PASS`.
5. Run `python scripts/validate_stage02.py <workspace> --strict-pass --output docs/02-stage02-validation.json`.
6. If strict validation fails, revert Stage 02 to `IN_PROGRESS`, repair, and validate again.

If code execution is unavailable, manually apply the same contract. Never claim the bundled validator ran when it did not.

## Required artifacts

Create or update:

- `docs/02-ui-architecture.md`
- `docs/02-design-system.md`
- `docs/02-stage-03-handoff.md`
- `design/tokens.json`
- `project-state.json`

Create when the validator runs:

- `docs/02-stage02-validation.json`

Update `docs/01-research-evidence.md` or the shared evidence structure only when new Stage 02 research materially contributes and the project convention allows the shared file to continue across stages.

## Semantic quality gate

PASS only when all are true:

- Stage 01 inputs are sufficiently complete and no unresolved blocker prevents safe design;
- product scope has not been silently redefined;
- every primary role and journey has coherent UI coverage;
- screen, flow, navigation, layout, and component IDs are stable and traceable;
- every important screen has relevant loading, empty, error, permission, success, and recovery behavior;
- layout behavior is intentional across required viewport ranges;
- reusable component contracts cover repeated interaction patterns;
- token architecture is semantic and implementation-neutral;
- forms and destructive actions have explicit validation, confirmation, and recovery behavior;
- accessibility behavior is actionable and mapped to implementation/testing obligations;
- localization/RTL behavior is explicit where relevant;
- content/microcopy rules prevent ambiguous operational messages;
- Stage 03 can implement the frontend without inventing core navigation, states, component behavior, or design-system rules;
- traceability contains no material orphan or uncovered item;
- machine validation passes when tools are available.

If any condition fails, repair and revalidate instead of emitting PASS.

## Stage boundary

Do not implement:

- React, Next.js, Vue, Angular, Svelte, HTML/CSS application screens, or other frontend application code;
- backend services, controllers, jobs, or business logic;
- database tables, migrations, indexes, or physical schemas;
- API endpoints or API implementation;
- authentication or authorization enforcement;
- deployment, CI/CD, container, server, or cloud infrastructure;
- pixel-for-pixel competitor cloning.

Allowed outputs include architecture/specification Markdown, machine-readable design tokens, validation reports, state updates, diagrams expressed as documentation, and other design-stage contracts that do not implement the application.

## Completion markers

On success, end with exactly:

`STAGE_02_STATUS: PASS`

`NEXT_STAGE: 03-frontend-architecture`

If a true blocking external dependency remains, update state to `BLOCKED` and end with exactly:

`STAGE_02_STATUS: BLOCKED`

`NEXT_STAGE: NONE`
