# UI Architecture Contract

## Table of contents

1. Purpose
2. Stable identifiers
3. Navigation contract
4. Flow contract
5. Screen contract
6. Layout contract
7. Permission-intent rules
8. Route and entry-point rules
9. Operational completeness
10. Anti-patterns

## 1. Purpose

UI architecture is the structural contract connecting Stage 01 product behavior to Stage 03 implementation. It must answer what surfaces exist, who can reach them, why they exist, how users move between them, what states they expose, and which reusable patterns they use.

Do not begin from visual styling. Begin from actors, journeys, requirements, permissions, data visibility, and operational outcomes.

## 2. Stable identifiers

Use:

- `NAV-###` for navigation structures or rules.
- `FLW-###` for UI flows.
- `SCR-###` for route-level screens or major modal surfaces.
- `LAY-###` for reusable page layout patterns.
- `CMP-###` for component families.
- `UXR-###` for cross-cutting interaction rules.
- `DSD-###` for material design-system decisions.

Never reuse an ID for a different concept. Never renumber surviving items to close gaps.

## 3. Navigation contract

For each `NAV-*` define:

- Name.
- Applicable roles.
- Navigation level: global, primary, secondary, contextual, utility.
- Items and destinations.
- Visibility conditions.
- Active-state behavior.
- Deep-link behavior.
- Mobile/adaptive transformation.
- Breadcrumb or back-navigation behavior where relevant.
- Related `ROLE-*`, `JRN-*`, and `SCR-*`.

Navigation must reflect permission intent but must never be described as the security enforcement mechanism.

## 4. Flow contract

For each `FLW-*` define:

- Goal/outcome.
- Actor(s).
- Trigger/start condition.
- Preconditions.
- Ordered steps.
- Branches and decision points.
- Validation points.
- External-system handoffs.
- Success termination.
- Cancellation behavior.
- Error/retry/recovery behavior.
- Related screens.
- Related Stage 01 IDs.

A primary journey without a UI flow is a coverage defect.

## 5. Screen contract

For each `SCR-*` define:

- Screen name.
- Purpose/outcome.
- Roles.
- Related journeys.
- Related requirements/rules/integrations.
- Entry points and route intent.
- Layout pattern ID.
- Primary action.
- Secondary actions.
- Required information/data.
- Permission/visibility behavior.
- Reusable component IDs.
- State coverage.
- Validation behavior.
- Responsive behavior.
- Accessibility obligations.
- Localization/RTL obligations.
- Exit/navigation behavior.
- Open questions/assumptions.

A screen is not complete if it only describes the happy-path screenshot.

## 6. Layout contract

For each `LAY-*` define:

- Purpose and applicable screen types.
- Regions and hierarchy.
- Content width strategy.
- Scrolling owner.
- Sticky/fixed regions.
- Dense versus comfortable behavior.
- Responsive region reordering.
- Sidebars and drawers.
- Header/footer behavior.
- Empty/error layout behavior.

Prefer a small set of reusable layouts over bespoke per-page shells.

## 7. Permission-intent rules

Distinguish:

- discoverability: whether the user can see that a capability exists;
- visibility: whether content or controls appear;
- affordance: whether an action appears enabled/actionable;
- authorization: whether the backend actually permits the action.

Stage 02 owns the first three as UX contracts. It does not implement or guarantee authorization.

For actions that are visible but unavailable, define whether the control is hidden, disabled with an explanation, or replaced by a request-access path. Choose based on product policy and user value, not a blanket rule.

## 8. Route and entry-point rules

When route architecture is in scope, define intent rather than framework syntax:

- public vs authenticated surface;
- role-specific entry routes;
- canonical detail route behavior;
- direct-link access behavior;
- missing/removed resource behavior;
- return/back behavior after nested workflows;
- query/filter persistence expectations where relevant.

Do not select router libraries or implement route code in Stage 02.

## 9. Operational completeness

High-risk or high-frequency workflows should explicitly cover:

- first use;
- repeat use;
- no-data state;
- filtered no-results state;
- slow response;
- partial response;
- failed integration;
- stale information;
- permission loss;
- session expiry expectation;
- concurrent update conflict when relevant;
- destructive action;
- retry and recovery;
- completion acknowledgement.

## 10. Anti-patterns

Do not:

- create screens that are not justified by product scope;
- use one generic dashboard to hide missing journey analysis;
- split one task across unnecessary pages because a reference product does;
- duplicate the same filter/table/form pattern under different names;
- treat a modal as a default solution for every secondary task;
- assume desktop layout can simply compress onto mobile;
- hide critical error states from the architecture document;
- use page titles as component names;
- encode backend authorization only through UI visibility.
