# Stage 03 Detailed Execution Workflow

## Overview

Execute in this order:

1. Preflight and repository inventory.
2. Baseline verification.
3. Requirement-to-route traceability.
4. Architecture normalization.
5. Route/screen implementation.
6. Design-system/responsive/RTL implementation.
7. Data/API/state/forms implementation.
8. Accessibility/security/resilience implementation.
9. Testing.
10. Runtime/visual QA.
11. Full final verification.
12. Documentation and state handoff.
13. Gate decision.

Do not skip from inventory directly to documentation.

## A. Preflight

Capture:

- repository root;
- frontend root;
- monorepo/workspace structure;
- current branch if available;
- current dirty files;
- package manager and lockfile;
- Node/runtime constraints;
- framework/router/rendering model;
- styling/design-system approach;
- state/query/form libraries already present;
- test runners;
- build/lint/typecheck scripts;
- environment configuration pattern;
- Stage 01/02 artifacts and status.

Never overwrite a dirty file without first understanding whether the change is user-owned and how to preserve it.

## B. Baseline verification

Before large changes, run existing fast checks where feasible to distinguish inherited failures from newly introduced failures.

Record commands and outcomes. A baseline failure does not excuse leaving the final tree broken. Determine whether it falls inside Stage 03 scope and repair it when it does.

Useful sequence for Node projects:

1. dependency availability/install state;
2. lint;
3. typecheck;
4. tests;
5. production build.

Do not reinstall dependencies blindly if the repository is already installed and healthy. Do not delete lockfiles to make resolution easier.

## C. Build the traceability ledger

Create an internal or documented table with at least:

| Requirement/Journey | Actor | Route/Screen | State coverage | Implementation | Test/QA evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |

Every critical journey must have a final status. Do not accept "screen exists" as journey coverage if its actions/states are inert.

## D. Architecture pass

Inspect for:

- multiple competing route definitions;
- app-level providers instantiated more than once;
- circular feature dependencies;
- shared components importing feature internals;
- API calls embedded in low-level presentational components;
- server state duplicated into global client stores;
- route-specific business state leaking globally;
- inconsistent type definitions for the same domain object;
- copy-pasted validation schemas;
- inconsistent error shapes;
- duplicated design tokens or raw values that should be semantic;
- hard-coded LTR/RTL assumptions;
- runtime-only dependencies accidentally in devDependencies or vice versa if this breaks production.

Normalize only where it increases correctness or maintainability for actual current scope.

## E. Route implementation order

Implement in dependency order:

1. application shell/providers;
2. global layouts/navigation;
3. public/entry routes;
4. authentication UX interfaces if required;
5. primary role dashboards/workspaces;
6. critical create/edit/submit journeys;
7. detail/history/status views;
8. settings/support/secondary routes;
9. not-found/forbidden/error routes.

For each route verify:

- route resolves;
- title/metadata where relevant;
- correct layout;
- responsive behavior;
- RTL/LTR behavior;
- loading state;
- empty state when data can be empty;
- success content;
- recoverable error state;
- permission state if applicable;
- action feedback;
- no dead controls;
- keyboard reachable controls;
- no console/runtime error caused by the route.

## F. Component implementation order

Use layers:

1. tokens;
2. primitives;
3. composed reusable patterns;
4. feature components;
5. route compositions.

Do not place product/business semantics into generic primitives. Do not expose every component as shared merely because it appears twice if the two uses are likely to evolve independently.

## G. Data and API workflow

For each external data need:

1. identify the domain type;
2. define request/response shape from approved evidence;
3. define a typed client method or repository adapter;
4. normalize transport/server errors to a stable frontend error model;
5. connect server-state cache/query behavior;
6. connect route/component loading and error states;
7. isolate mock/fixture behavior to test/development;
8. test success and representative failure behavior.

If endpoint details are not yet finalized, define the minimum explicit interface required by the frontend and add it to Stage 04/06 handoff. Do not invent a production URL and pretend it exists.

## H. Form workflow

For each non-trivial form:

1. derive fields and rules from Stage 01/02;
2. define typed form value/schema;
3. render persistent labels and help text where needed;
4. connect validation to fields and summary/status behavior;
5. preserve entered data after recoverable server error unless policy requires reset;
6. disable or guard duplicate submission while pending;
7. map server validation errors to fields/general form errors;
8. show success outcome without ambiguous silent completion;
9. handle upload progress/constraints when files exist;
10. handle dirty navigation when losing unsaved work would be harmful;
11. test keyboard submit and invalid state;
12. never trust client validation as server enforcement.

## I. Responsive and RTL workflow

For each layout family test content stress, not only ideal samples:

- short and long titles;
- long localized strings;
- empty values;
- large numeric values;
- narrow viewport;
- intermediate viewport;
- wide viewport;
- mixed RTL/LTR values;
- table overflow;
- modal width/height;
- sticky/fixed UI;
- long menus and dropdowns.

Prefer logical CSS properties (`margin-inline`, `padding-inline`, `inset-inline`, logical borders/radii where appropriate) over mirrored one-off overrides.

## J. Accessibility workflow

For each critical journey:

1. navigate from top to completion using keyboard;
2. verify meaningful focus order;
3. verify focus visibility;
4. verify dialog/menu focus behavior;
5. verify input labels and error association;
6. verify icon-only controls have accessible names;
7. verify dynamic success/error/loading changes are perceivable;
8. verify no interaction requires pointer hover only;
9. verify reduced motion for decorative animation;
10. verify semantic structure and headings.

If automated a11y tools exist, run them, but never treat zero automated findings as complete accessibility proof.

## K. Security hygiene workflow

Search and inspect for:

- `dangerouslySetInnerHTML` or equivalent raw HTML rendering;
- direct DOM HTML injection;
- untrusted URL navigation;
- redirect query parameters;
- authentication tokens in logs;
- secrets in source/public env examples;
- verbose API payload logging;
- insecure assumptions around hidden/disabled UI;
- production fixture fallbacks;
- `eval`, dynamic code construction, or untrusted script injection;
- accidental exposure of private server-only environment variables to client bundles.

Repair in-scope issues. Hand backend/header controls to later stages with precise requirements.

## L. Testing workflow

Use the existing test pyramid and tooling. Add targeted tests that protect Stage 03 contracts.

Minimum preferred set when feasible:

- utility/schema unit tests for non-trivial pure logic;
- component/interaction tests for critical forms or complex controls;
- route smoke tests for critical route families;
- tests for loading/empty/error states where regressions are likely;
- one representative critical-journey integration/E2E path when the project already has an E2E harness or adding one is proportionate.

Avoid snapshot-only testing for behavior that should be asserted semantically.

## M. Runtime/visual QA workflow

When a browser is available:

1. start the app using its real dev/preview command;
2. use representative local/test data through approved adapters;
3. visit required routes;
4. test responsive widths;
5. test required locales/directions;
6. capture screenshots if the environment supports evidence artifacts;
7. inspect console/network issues;
8. fix defects;
9. repeat affected paths;
10. perform a final smoke pass after the last code change.

## N. Final verification

Rerun the complete mandatory checks against the final working tree. The final report must not cite stale pre-fix results.

Confirm:

- no mandatory command fails;
- no critical journey remains missing;
- no known production mock fallback remains;
- no known frontend secret exposure remains;
- report matches actual repository state;
- `project-state.json` matches actual evidence;
- handoff needs are explicit and actionable.
