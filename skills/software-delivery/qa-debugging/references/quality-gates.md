# Stage 10 Quality Gates

## Table of contents

1. Gate philosophy
2. Gate A - Stage eligibility and environment
3. Gate B - Traceability and coverage
4. Gate C - Core functional behavior
5. Gate D - Authorization and data integrity
6. Gate E - UI and accessibility
7. Gate F - Automated verification
8. Gate G - Defect closure
9. Gate H - Evidence and artifacts
10. Gate I - Stage 11 readiness
11. BLOCKED conditions
12. PASS decision algorithm

## 1. Gate philosophy

Stage 10 is binary at the orchestrator boundary: PASS or BLOCKED. P2/P3 findings may remain only when they are explicitly documented and do not violate a mandatory gate.

Do not create a hidden third state such as "conditional pass" for an open release blocker.

## 2. Gate A - Stage eligibility and environment

PASS this gate only if:

- Stage 09 is confirmed PASS;
- the tested release candidate is identifiable;
- the application can start in the available safe test environment;
- required local/test dependencies can be exercised sufficiently to verify critical behavior;
- test execution does not depend on inventing production secrets.

BLOCK if the application cannot run or the critical environment cannot be established.

## 3. Gate B - Traceability and coverage

PASS only if:

- `docs/10-qa-matrix.md` exists;
- release-critical requirements/journeys are represented;
- critical roles are represented;
- privileged capabilities include allow/deny coverage;
- important state transitions include valid/invalid coverage;
- every critical matrix row is PASS or a documented true blocker;
- every FAIL row maps to a defect.

An omitted critical row is not a pass.

## 4. Gate C - Core functional behavior

PASS only if:

- every release-critical journey executed successfully after final fixes;
- successful UI flows persist correct canonical state;
- duplicate/retry behavior is safe for critical mutations;
- critical partial-failure paths do not leave known corrupt/inconsistent state;
- required cross-role/downstream effects behave correctly.

## 5. Gate D - Authorization and data integrity

PASS only if:

- no known P0/P1 auth bypass remains;
- no known P0/P1 cross-owner/cross-tenant exposure remains;
- critical protected operations enforce server-side authorization;
- no known P0/P1 data corruption/integrity defect remains;
- high-value state transitions obey domain rules;
- critical mutation duplicates/replays do not create unsafe side effects.

This gate cannot be waived by hiding UI controls.

## 6. Gate E - UI and accessibility

For products with UI, PASS only if:

- core flows are usable at required/representative viewport classes;
- no release-blocking clipping/overflow makes critical actions unreachable;
- required RTL/LTR behavior works for critical screens;
- critical flows are keyboard operable to the level required by project/accessibility commitments;
- no known P0/P1 accessibility defect blocks core operation;
- modal/focus/error behavior does not make critical flows unusable.

If the product has no UI, mark this gate N/A with reason.

## 7. Gate F - Automated verification

PASS only if all project-required executable checks pass after final fixes, such as:

- build/compile;
- lint;
- typecheck;
- unit tests;
- integration tests;
- E2E tests;
- migration/schema checks;
- security regression checks.

If a check is genuinely unavailable, document why and assess whether the missing evidence blocks a critical claim. Do not equate `NOT RUN` with PASS.

## 8. Gate G - Defect closure

PASS only if:

- open P0 count = 0;
- open P1 count = 0;
- every fixed P0/P1 has regression evidence;
- failed fix attempts are not left as uncontrolled code changes;
- remaining P2/P3 issues are documented;
- no issue was reclassified downward solely to make the gate pass.

## 9. Gate H - Evidence and artifacts

PASS only if:

- `docs/10-qa-report.md` exists and is complete;
- `docs/10-known-issues.md` exists;
- `docs/10-qa-matrix.md` exists;
- report, matrix, defect statuses, and known issues are consistent;
- exact final verification commands/results are recorded;
- environment and constraints are recorded;
- project state is updated without deleting unknown keys;
- `scripts/validate_stage10_artifacts.py` passes when executable.

## 10. Gate I - Stage 11 readiness

PASS only if Stage 11 can focus on deployment/production preparation rather than product repair.

Stage 11 may still need to verify:

- production configuration;
- secrets injection;
- DNS/TLS;
- production migrations;
- infrastructure health;
- deployment rollback;
- production smoke after authorized deployment.

But Stage 11 must not inherit:

- known broken core journey;
- open P0/P1 product defect;
- unresolved serious auth/data-integrity issue;
- failing required build/test suite;
- a release candidate that cannot start.

## 11. BLOCKED conditions

Stage 10 must be BLOCKED when any applies:

- Stage 09 did not pass;
- release candidate cannot be started/tested sufficiently;
- open P0 or P1 exists;
- critical authorization/data-integrity gate fails;
- one or more release-critical journeys are known failing;
- a critical journey cannot be verified due to unavailable required dependency and no safe substitute can establish readiness;
- project-required build/type/test gate is failing due to release code;
- evidence is insufficient to support a mandatory gate;
- artifact state is materially inconsistent and cannot be corrected.

## 12. PASS decision algorithm

Use this exact decision order:

1. Confirm Stage 09 PASS. If no -> BLOCKED.
2. Confirm release candidate starts and critical environment is usable. If no -> BLOCKED.
3. Confirm all critical matrix rows are executed or explicitly blocked. If a critical row is FAIL/BLOCKED without acceptable readiness evidence -> BLOCKED.
4. Confirm open P0/P1 count is zero. If no -> BLOCKED.
5. Confirm authorization/data-integrity mandatory gate. If fail -> BLOCKED.
6. Confirm project-required executable automated checks. If fail due to release code -> BLOCKED.
7. Confirm fixed high-severity defects have regression evidence. If no -> BLOCKED.
8. Confirm artifacts/evidence consistency. If no -> correct artifacts; if impossible -> BLOCKED.
9. Confirm residual P2/P3 issues are genuinely non-blocking and documented.
10. Confirm Stage 11 can deploy without product repair.
11. Only then emit Stage 10 PASS markers.
