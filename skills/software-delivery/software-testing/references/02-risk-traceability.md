# Risk Model and Requirement Traceability

## Purpose

Turn requirements and known risks into a prioritized, auditable test plan. Ensure critical behavior cannot disappear between implementation and test execution.

## Table of contents

1. Source inventory
2. Risk priorities
3. Risk scoring guidance
4. Test-layer selection
5. Traceability matrix
6. Positive/negative/boundary/recovery dimensions
7. Cross-cutting risk families
8. Coverage rules
9. Updating the matrix during execution

## 1. Source inventory

Collect test obligations from all available authoritative project artifacts:
- product requirements;
- acceptance criteria;
- API/OpenAPI contracts;
- workflow/state-machine documentation;
- database constraints;
- role/permission matrix;
- ownership/tenant rules;
- Stage 08 security findings/fixes;
- incident/bug history;
- migration plans;
- integration contracts;
- non-functional requirements that are testable in Stage 09;
- existing tests representing prior behavior.

Do not treat implementation code as the only specification. Code can contain the defect being tested.

## 2. Risk priorities

Use four priorities.

### P0 — Catastrophic or business-critical

Use P0 when failure can cause one or more of:
- unauthorized access to sensitive data/actions;
- irreversible or severe data corruption/loss;
- incorrect money movement or material financial loss;
- broken core transaction/workflow preventing primary product use;
- cross-tenant data exposure;
- critical legal/compliance failure represented in project requirements;
- systemic outage caused by a common path;
- unrecoverable migration failure for supported upgrade path.

P0 requires explicit automated evidence before PASS.

### P1 — High impact

Use P1 for:
- major feature failure;
- incorrect important calculation;
- significant auth/ownership denial path;
- data-integrity issue with bounded recovery;
- high-volume API contract break;
- major user journey failure;
- duplicate processing/idempotency defect with material effects.

P1 normally requires explicit automated evidence before PASS.

### P2 — Medium impact

Use P2 for:
- secondary flows;
- recoverable edge cases;
- non-critical validation;
- meaningful but non-core UI interaction;
- lower-risk integration behavior.

### P3 — Low impact

Use P3 for:
- cosmetic/non-critical behavior better suited for Stage 10;
- low-risk helpers;
- rare low-impact branches.

Do not misuse P3 to hide untested complexity.

## 3. Risk scoring guidance

When priority is unclear, consider:
- impact severity;
- likelihood/frequency;
- detectability before production;
- reversibility/recovery cost;
- security/privacy exposure;
- blast radius;
- complexity/change size;
- history of defects in the area.

A simple score can support judgment, but do not let arithmetic override obvious criticality.

Example optional scoring:

`risk_score = impact(1-5) × likelihood(1-5) × detectability(1-3)`

Then calibrate priority to project context. Security or money movement may be P0 even with low observed frequency.

## 4. Test-layer selection

Choose the lowest layer that can credibly prove the requirement, then add higher-layer tests only for integration confidence.

### Prefer unit tests when
- behavior is pure business logic;
- boundary integration is irrelevant;
- failure can be fully observed without external systems.

### Prefer integration tests when
- SQL constraints/transactions matter;
- repository mappings matter;
- queue/cache/storage wiring matters;
- framework middleware or dependency injection matters;
- serialization/persistence behavior matters.

### Prefer API/contract tests when
- status/error shape matters;
- authentication middleware matters;
- request/response schemas matter;
- pagination/filtering/idempotency matters;
- multiple internal layers must collaborate.

### Prefer E2E when
- confidence depends on full user journey wiring;
- frontend + backend + auth + persistence integration is material;
- redirect/session/browser behavior matters;
- a critical workflow can regress despite lower-layer tests.

Avoid testing the exact same assertion at every layer without a risk reason.

## 5. Traceability matrix

Maintain a table in `docs/09-test-plan.md` with at least:

| Source ID | Priority | Requirement/Risk | Failure impact | Test layer | Planned test IDs | Positive | Negative | Boundary | Recovery | Status |
|---|---|---|---|---|---|---|---|---|---|---|

Use stable test IDs such as:
- `UT-AUTH-001`;
- `IT-ORDER-003`;
- `API-PAY-005`;
- `SEC-RBAC-004`;
- `MIG-USER-002`;
- `E2E-CHECKOUT-001`.

Map one source ID to multiple test IDs when needed. Map one test to multiple source IDs only when the test truly proves each requirement.

## 6. Positive, negative, boundary, and recovery dimensions

For each P0/P1 requirement, explicitly consider four dimensions.

### Positive

Can a legitimate actor complete the intended action with valid input?

### Negative

Are invalid/forbidden actions rejected with the correct safety behavior?

Examples:
- unauthenticated;
- wrong role;
- wrong owner;
- wrong tenant;
- invalid state transition;
- malformed payload;
- duplicate request.

### Boundary

Test limits and partitions that commonly fail:
- minimum/maximum;
- empty/null/missing;
- just below/at/above threshold;
- Unicode/RTL/locale;
- date boundaries/timezone;
- pagination edges;
- large but allowed payloads;
- precision/rounding.

### Recovery

When failure occurs, does the system remain correct and can the operation safely retry or recover?

Examples:
- transaction rollback;
- idempotent retry;
- failed upload cleanup;
- queue redelivery;
- partial external failure;
- optimistic-lock conflict.

Not every requirement needs all four dimensions. Document `N/A` deliberately rather than ignoring the dimension.

## 7. Cross-cutting risk families

Always scan for these families when relevant:
- authentication/session/token lifecycle;
- authorization/RBAC/ABAC;
- object ownership/IDOR/BOLA;
- tenant isolation;
- money/credits/limits;
- duplicate submission/idempotency;
- concurrency/races;
- state-machine transitions;
- audit/logging side effects;
- file upload/content handling;
- data migration/backfill;
- timezone/calendar/locale;
- pagination/filtering/sorting;
- async processing/eventual consistency;
- external provider failures;
- cache invalidation;
- retry semantics;
- privacy/PII redaction.

## 8. Coverage rules

Before PASS:
- P0 covered = 100% by credible automated evidence;
- P1 covered = 100% unless a documented equivalent automated control provides the same confidence;
- Stage 08 reproducible fixes = regression covered;
- authorization denial coverage = complete for critical role/ownership/tenant boundaries;
- known fixed Stage 09 defects = regression covered.

A coverage item is not "covered" merely because a test file exists. It must have a passing executed test or a justified equivalent automated evidence item.

## 9. Updating the matrix during execution

Treat the matrix as live.

When a new defect reveals a missing risk:
1. add a source/risk entry;
2. assign priority;
3. add regression test ID;
4. update plan/status;
5. rerun relevant suites;
6. update final summary counts.

When implementation behavior conflicts with a requirement, keep the original requirement visible and record the conflict. Do not rewrite history to match the code.
