# Stage 03 Handoff Report Template

Create `docs/03-frontend-architecture.md` with the following structure. Adapt subheadings to the actual project, but do not omit required evidence sections.

# Stage 03 - Frontend Architecture and Implementation

## 1. Executive summary

State what was implemented/repaired, frontend root, framework/runtime, current stage status, and whether any residual risk remains.

## 2. Inputs and traceability

Record:

- Stage 01 artifact paths reviewed;
- Stage 02 artifact paths reviewed;
- Stage 02 PASS evidence;
- key actors/journeys covered;
- any approved/safety/accessibility corrections to prior decisions.

## 3. Repository and stack

Record:

- frontend root/workspace;
- framework/router/rendering model;
- language/type system;
- styling/design-system stack;
- data/query/state/form libraries;
- package manager;
- test stack;
- important compatibility constraints.

## 4. Source architecture

Show the actual relevant source tree and explain boundaries among app/routes, features, shared UI, domain types, API/services, state, localization, utilities, and tests.

## 5. Route and journey coverage

Use a table:

| Actor/Journey | Route(s) | Implementation status | States implemented | Verification |
| --- | --- | --- | --- | --- |

List every critical journey.

## 6. Design system and responsive implementation

Record:

- token/primitives strategy;
- reusable component families;
- responsive layout decisions;
- overflow/table/dialog strategy;
- motion/reduced-motion behavior;
- known visual constraints.

## 7. Localization and RTL/LTR

Record:

- locale and direction source;
- logical-property strategy;
- mixed-direction handling;
- number/date/identifier behavior;
- routes/locales actually reviewed.

## 8. API and data boundary

Record:

- transport/client location;
- typed contracts/models;
- error normalization;
- query/cache strategy;
- production vs test/dev adapter behavior;
- exact backend contracts Stage 04 must satisfy.

## 9. State management

Explain what is local UI state, URL state, server state, form state, and global client state, with rationale for any global store.

## 10. Forms and validation

List critical forms, validation strategy, server-error mapping, pending/duplicate-submit behavior, file-upload handling if applicable, and representative tests.

## 11. Accessibility

Record manual and automated evidence for:

- semantics/headings;
- keyboard/focus;
- labels/errors;
- modal/menu behavior;
- dynamic status announcements;
- reduced motion;
- any unresolved non-blocking accessibility risk.

Do not claim formal WCAG compliance without appropriate evidence.

## 12. Security/privacy hygiene

Record findings and decisions for:

- raw/untrusted HTML;
- untrusted redirects/URLs;
- client-exposed environment variables;
- token/sensitive logging;
- production fixtures/debug code;
- frontend role guards vs required backend authorization.

## 13. Performance and production behavior

Record relevant build/bundle observations, route splitting, image/media handling, list rendering, known hotspots, and Stage 01 performance-budget results if budgets exist.

## 14. Verification evidence

Use a table:

| Check | Command/tool | Final status | Evidence/notes |
| --- | --- | --- | --- |
| Format | ... | PASS/FAIL/NOT_RUN/N/A | ... |
| Lint | ... | ... | ... |
| Typecheck | ... | ... | ... |
| Tests | ... | ... | ... |
| Build | ... | ... | ... |
| Runtime smoke | ... | ... | ... |
| Responsive/RTL | ... | ... | ... |
| Accessibility | ... | ... | ... |
| Security hygiene | ... | ... | ... |

Only list commands that actually ran.

## 15. Material changes

List major created/updated files or directories and why they changed. Do not dump every generated artifact if the list is enormous; group coherent changes.

## 16. Assumptions, deviations, and residual risks

Separate:

- safe assumptions;
- documented corrections/deviations from Stage 02;
- non-blocking residual risks;
- blockers if status is BLOCKED.

## 17. Stage 04 backend handoff

Give exact contracts Stage 04 must implement, including endpoint/domain operation names, expected request/response/error behavior, auth/session assumptions, pagination/filter/sort needs, upload/download needs, and server authorization requirements.

Do not invent endpoint URLs when prior stages did not approve them; describe domain operations precisely instead.

## 18. Later integration handoff

List what the integration stage must replace/connect/verify, including development adapters, environment variables, error mappings, and end-to-end journeys.

## 19. Quality gate decision

List G0-G10 statuses from `references/03-quality-gates.md` and explain any `NOT_APPLICABLE` or `NOT_RUN` result.

Finish the document with the actual Stage 03 status and next stage.
