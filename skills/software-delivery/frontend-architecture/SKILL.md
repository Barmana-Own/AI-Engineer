---
name: frontend-architecture
description: "Stage 03 of the Barmana autonomous full-stack delivery workflow. Use after Stage 02 has passed when a project must turn approved product requirements and UI/UX architecture into a production-quality frontend implementation. Inspect and modify the real repository; establish routes, layouts, design-system primitives, responsive/RTL behavior, typed API boundaries, forms, state/data patterns, accessibility, error states, security hygiene, tests, and build quality. Repair partial or inconsistent frontend work instead of merely documenting it. Do not implement backend business logic, database persistence, or deployment infrastructure. Do not allow Stage 04 until mandatory Stage 03 evidence and quality gates pass."
---

# Stage 03 - Frontend Architecture and Implementation

## Mission

Act as the senior frontend engineer responsible for converting the approved Stage 01 requirements and Stage 02 UI/UX architecture into a maintainable, production-grade frontend implementation.

Do real repository work. Inspect, design, implement, repair, test, verify, document, and hand off. Do not finish with recommendations alone when file/code tools are available.

The stage is complete only when the implementation and mandatory evidence satisfy the quality gate. The purpose of this stage is to leave Stage 04 and later integration stages with a stable frontend contract, not a prototype that merely looks complete.

## Non-negotiable execution rules

1. Read the project before editing it.
2. Require evidence that Stage 02 passed before treating Stage 03 as eligible to complete.
3. Preserve valid decisions from earlier stages unless they create a security defect, implementation contradiction, inaccessible design, or true blocker. Document every material correction.
4. Work inside the existing architecture when it is sound. Do not rewrite or replace the stack merely because another stack is preferred.
5. Preserve the existing package manager and lockfile strategy. Do not perform broad dependency upgrades unless required to make the approved design executable or to resolve a concrete compatibility/security blocker.
6. Inspect version-control status before editing. Never use destructive reset/clean commands and never discard unrelated user work.
7. Implement the full relevant change in project files. Do not substitute chat snippets for repository modifications when repository tools are available.
8. Never hide unfinished behavior behind production mock data, fake success responses, hard-coded credentials, TODO-only screens, disabled controls, or silent no-op handlers.
9. Never claim a command, test, browser check, accessibility check, or build passed unless it actually ran and its result is known.
10. Repeat implementation -> verification -> repair until all mandatory checks pass or a true external blocker remains.
11. Treat frontend authorization checks as UX only. Do not claim client-side route guards enforce backend security.
12. Keep backend business logic, database schema/migrations, server-side authorization enforcement, production infrastructure, and deployment configuration outside this stage except for explicit frontend-facing contracts or requirements that must be handed off.
13. Preserve unknown fields in `project-state.json`. Update only this stage's state plus workflow pointers required by the orchestrator.
14. Do not mark `PASS` if a mandatory executable verification failed or could not be executed in an environment where execution is required to establish correctness.
15. Do not move to the next stage merely because documentation exists.

## Progressive references

Read these files when their topic becomes relevant. They are part of the skill contract.

- `references/00-stage-contract.md` - preconditions, artifact discovery, blockers, allowed scope, and Stage 02 reconciliation.
- `references/01-execution-workflow.md` - detailed repository workflow from preflight through final verification.
- `references/02-implementation-standards.md` - frontend architecture, routing, design system, API, state, forms, accessibility, RTL/i18n, security, performance, and testing standards.
- `references/03-quality-gates.md` - mandatory gate matrix and exact PASS/BLOCKED rules.
- `references/04-project-state-schema.md` - canonical Stage 03 state shape and safe merge behavior.
- `references/05-handoff-report-template.md` - required `docs/03-frontend-architecture.md` structure and final evidence summary.

For Node-based frontends, use `scripts/frontend_quality_gate.py` when possible to run and record the repository's declared quality scripts consistently. The script does not replace browser/visual/accessibility review.

## Phase 0 - Establish execution context

Before making changes:

1. Find the repository root and determine whether the frontend is:
   - a standalone app;
   - a subdirectory such as `frontend/`, `web/`, `client/`, or `apps/web/`;
   - part of a monorepo;
   - not yet initialized.
2. Read `project-state.json` if it exists.
3. Resolve the actual Stage 01 and Stage 02 artifact paths from project state first; otherwise discover likely `docs/01-*` and `docs/02-*` artifacts.
4. Read Stage 01 requirements, actor/role definitions, journeys, business rules, NFRs, assumptions, and risks.
5. Read Stage 02 route/screen inventory, responsive behavior, design system, content hierarchy, states, RTL/i18n, accessibility, and approved deviations.
6. Confirm Stage 02 status is `PASS`. If it is explicitly failed or blocked, stop Stage 03 as `BLOCKED`.
7. Inspect the existing frontend source, package manifest, lockfile, scripts, framework config, TypeScript config, lint/format config, test config, environment examples, and current build status.
8. Inspect version-control status and preserve unrelated changes.
9. Create an implementation ledger mapping required routes/journeys/states to repository locations and verification evidence.

Follow `references/00-stage-contract.md` for exact artifact and blocker rules.

## Phase 1 - Reconcile approved design with repository reality

Create a traceable implementation plan before large edits:

1. Map every required actor and critical journey to routes/screens.
2. Map every Stage 02 screen to one of: `implemented`, `partial`, `missing`, `obsolete`, or `conflicting`.
3. Identify reusable shells, layouts, primitives, feature boundaries, domain types, API clients, and state ownership.
4. Detect design drift: duplicate UI primitives, inconsistent tokens, route naming conflicts, missing empty/error states, hard-coded directionality, and ad hoc data access.
5. Detect technical constraints in the current repo: SSR/CSR behavior, router type, package versions, build target, browser target, component library, CSS strategy, and test stack.
6. Resolve non-critical ambiguity using the safest consistent interpretation and record the assumption.
7. If Stage 02 contains an impossible, insecure, or accessibility-breaking decision, make the smallest necessary correction, preserve intent, and record the reason and impact.
8. Do not silently invent new product scope.

## Phase 2 - Establish or repair the frontend architecture

Use the existing project layout when coherent. Otherwise create a clear separation among:

- application bootstrap and providers;
- route definitions and route-level layouts;
- feature modules;
- reusable UI primitives and design-system components;
- domain types/schemas;
- API/transport adapters;
- server-state/query utilities;
- global client state only where justified;
- forms/validation;
- localization/direction helpers;
- shared utilities;
- tests and fixtures.

Do not create abstraction layers that have no current reuse or clear architectural purpose. Prefer explicit boundaries over speculative frameworks.

## Phase 3 - Implement route and journey coverage

For every required route and critical user journey:

1. Implement the route and appropriate layout/shell.
2. Implement page metadata/title behavior where the framework supports it.
3. Implement initial/loading/empty/partial/success/error states appropriate to the page.
4. Implement not-found and recoverable route errors.
5. Implement permission-denied/forbidden UX when roles require it, while explicitly treating it as UX rather than security enforcement.
6. Ensure direct navigation and refresh behavior are compatible with the selected router/runtime.
7. Ensure navigation does not strand keyboard or assistive-technology users.
8. Use route-level code splitting/lazy loading when supported and beneficial.
9. Verify links, breadcrumbs, tabs, back behavior, and deep-link parameters against Stage 02.

Maintain the implementation ledger as routes are completed.

## Phase 4 - Implement the design system, responsive behavior, and RTL

1. Create or normalize semantic design tokens for typography, spacing, radius, elevation, surfaces, borders, actions, feedback states, and motion as required by Stage 02.
2. Build reusable primitives for recurring controls instead of copy-pasting page-local variants.
3. Keep feature components domain-aware and primitives domain-neutral.
4. Use semantic variants rather than scattered magic values.
5. Reproduce approved states and interactions, not only the default screenshot state.
6. Implement mobile-first or Stage 02-defined responsive behavior and verify breakpoint transitions, wrapping, overflow, tables, forms, dialogs, sidebars, and navigation.
7. Prefer CSS logical properties so RTL/LTR mirroring is structural rather than patched per screen.
8. Apply document/component direction by locale and isolate mixed-direction values such as URLs, emails, identifiers, tracking codes, phone numbers, and code where needed.
9. Respect `prefers-reduced-motion` or equivalent reduced-motion requirements for non-essential animation.
10. Do not remove important information or controls on smaller screens merely to make the layout fit.

## Phase 5 - Implement data, API, state, and form boundaries

1. Define typed domain models and frontend-facing request/response contracts derived from approved requirements.
2. Centralize transport concerns: base URL, headers, credentials mode, cancellation, response decoding, normalized errors, and observability hooks.
3. Keep endpoint-specific logic out of generic UI primitives.
4. Keep server state in an appropriate query/cache layer when one exists; do not copy server state into global client stores without a concrete need.
5. Keep local interaction state local.
6. Use global client state only for truly cross-cutting client concerns.
7. Define query/cache keys deterministically and invalidate/refetch intentionally after mutations.
8. Use optimistic updates only when rollback/error recovery is implemented and the UX benefits justify them.
9. Implement forms with schema-based or equivalently typed validation, stable field/error mapping, server error handling, double-submit prevention, and accessible validation feedback.
10. Treat client validation as UX, never as the security boundary.
11. Put fixtures/mocks behind explicit test/development adapters. Production builds must not silently fall back to them.
12. Do not hard-code secrets, production tokens, private keys, or confidential configuration into frontend code or public environment variables.

## Phase 6 - Accessibility, resilience, and security hygiene

Apply the detailed rules in `references/02-implementation-standards.md`.

At minimum verify:

- semantic landmarks and heading structure;
- visible labels/instructions for inputs;
- keyboard operation and visible focus;
- focus containment/restoration for modal UI;
- accessible names for icon-only controls;
- meaningful status/error announcements where needed;
- no color-only communication of critical state;
- reduced-motion behavior for non-essential motion;
- error boundaries/fallbacks at appropriate scope;
- sanitized handling of untrusted HTML/URLs;
- no sensitive payloads in client logs;
- no secret-bearing public environment variables;
- no open-redirect pattern from untrusted navigation parameters;
- no false assumption that hidden UI equals authorization.

If Stage 02 requires a specific accessibility standard, treat that standard as the target and document verification evidence. Do not make unsupported compliance claims.

## Phase 7 - Performance and production behavior

1. Remove obvious unnecessary rerenders and unstable provider values in hot paths.
2. Avoid shipping large libraries for trivial functionality when an existing project utility suffices.
3. Keep route/feature code split where the framework makes it practical.
4. Optimize images/media according to framework capabilities and Stage 02 visual requirements.
5. Bound or virtualize genuinely large lists/tables when required by the NFRs or data volume.
6. Avoid serial request waterfalls that can safely execute concurrently.
7. Preserve SSR/streaming/server-component boundaries when the current framework relies on them.
8. Do not invent arbitrary performance claims. If Stage 01 defines budgets, test against them; otherwise record observed build/bundle evidence and known hotspots.
9. Ensure production mode does not expose debug panels, development fixtures, verbose logs, or source-only test controls.

## Phase 8 - Testing and verification loop

Use the repository's existing tools first. Add only the minimum compatible test tooling needed to verify critical behavior when no test stack exists.

Required verification categories:

1. formatting or format-check when configured;
2. lint;
3. typecheck for typed projects;
4. automated tests appropriate to the existing stack;
5. production build;
6. route/screen smoke coverage for critical journeys;
7. responsive/RTL review;
8. accessibility review;
9. production-mock and secret hygiene review.

For Node-based frontends, prefer running:

```bash
python3 <skill-root>/scripts/frontend_quality_gate.py --root <frontend-root> --output <repo-root>/docs/03-frontend-quality.json
```

The script detects the package manager, inspects `package.json`, runs declared quality scripts, and records actual results. Review its output rather than trusting exit code alone.

After every material repair, rerun the affected checks. Before final PASS, rerun the complete mandatory set so final evidence reflects the final tree.

Do not leave known test/build/lint/type failures for a later stage unless they are demonstrably caused by an external dependency that makes Stage 03 `BLOCKED`.

## Phase 9 - Runtime and visual QA

When a runtime/browser environment is available:

1. Start the actual frontend using the repository's documented development or preview command.
2. Visit every critical route and at least one representative secondary route per major layout family.
3. Verify desktop and narrow/mobile widths; add tablet/intermediate widths when Stage 02 defines behavior there.
4. Verify both RTL and LTR locales when both are required.
5. Check horizontal overflow, clipped content, stacking contexts, fixed/sticky elements, dialogs, menus, form errors, loading/empty/error states, images, and long localized text.
6. Exercise keyboard navigation through the main journey.
7. Verify browser console/runtime errors and failed network requests are understood and resolved or documented as external.
8. Re-test after visual fixes.

If no browser/runtime tool exists, do not claim visual QA ran. Perform code-level fallback review, mark browser checks `NOT_RUN`, and apply the quality-gate rules in `references/03-quality-gates.md`.

## Phase 10 - Documentation and state handoff

Create or update:

- the real frontend implementation in the repository;
- `docs/03-frontend-architecture.md`;
- `docs/03-frontend-quality.json` when the quality script is applicable;
- `project-state.json`.

Use `references/05-handoff-report-template.md` for the Stage 03 report.
Use `references/04-project-state-schema.md` for the Stage 03 state record.

The report must make the implementation auditable: changed architecture, route coverage, API boundary, state/forms strategy, accessibility/RTL/security decisions, commands actually executed, results, residual risks, explicit backend/integration needs, and Stage 04 handoff.

## Mandatory completion decision

Apply `references/03-quality-gates.md` exactly.

`PASS` means the repository is ready for Stage 04 without relying on unimplemented frontend fundamentals or known mandatory quality failures.

`BLOCKED` means a true external/precondition issue prevents a trustworthy Stage 03 completion. Examples include failed Stage 02, inaccessible required private specification, missing credentials needed to inspect an indispensable private dependency, or an environment limitation that prevents mandatory implementation/build verification and cannot be replaced with reliable evidence.

Do not use `BLOCKED` for ordinary engineering work that can be completed by editing the repository.

## Completion markers

On success, end with exactly:

`STAGE_03_STATUS: PASS`
`NEXT_STAGE: 04-backend-architecture`

On a true blocker, end with exactly:

`STAGE_03_STATUS: BLOCKED`
`NEXT_STAGE: NONE`
