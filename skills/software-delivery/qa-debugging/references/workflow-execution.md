# Stage 10 Execution Playbook

## Table of contents

1. Purpose
2. Phase 0 - Intake and evidence reconstruction
3. Phase 1 - Environment qualification
4. Phase 2 - QA strategy construction
5. Phase 3 - Automated baseline
6. Phase 4 - Product QA execution waves
7. Phase 5 - Defect triage
8. Phase 6 - Corrective patch loop
9. Phase 7 - Regression and burn-down
10. Phase 8 - Release-candidate closure
11. Phase 9 - Handoff
12. Conditional branches
13. Completion discipline

## 1. Purpose

Use this playbook to run Stage 10 as an engineering activity with explicit evidence, not as a checklist-writing exercise. Preserve traceability from requirement to scenario to observed result to defect to fix to regression evidence.

Maintain a working ledger while executing. Do not wait until the end to reconstruct what happened from memory.

## 2. Phase 0 - Intake and evidence reconstruction

### 2.1 Confirm stage eligibility

- Open `project-state.json` when present.
- Locate Stage 09 completion evidence and artifacts.
- Confirm Stage 09 is marked PASS or that equivalent authoritative evidence explicitly says the implementation/testing stage completed.
- If state and documents disagree, do not silently trust the most convenient source. Record the contradiction and inspect the newest passed-stage artifact.
- If Stage 09 is genuinely incomplete, stop normal QA and report the upstream blocker.

### 2.2 Identify the release candidate

Capture:

- repository root;
- package/workspace roots;
- branch and revision when available;
- dirty/uncommitted files;
- current runtime environment;
- application/service versions when discoverable;
- package manager and lockfiles;
- database engine and migration head;
- enabled integrations or mocks.

The goal is reproducibility. A later engineer should know what build was actually tested.

### 2.3 Reconstruct product intent

Read earlier artifacts and extract:

- actors and roles;
- primary user journeys;
- business rules;
- state transitions;
- acceptance criteria;
- role/permission rules;
- API contracts;
- data invariants;
- UI/UX behavior;
- supported locales, RTL/LTR behavior, date/time/currency rules;
- known risks and deferred work.

Do not rely only on route names or test names because implementation can omit required behavior.

### 2.4 Build a surface inventory

List all material surfaces:

- web/mobile/desktop user interfaces;
- public and private APIs;
- admin/operations panels;
- background workers;
- scheduled jobs;
- queues and consumers;
- webhooks;
- databases and migrations;
- caches;
- object/file storage;
- emails/SMS/push notifications;
- payment or identity integrations;
- import/export flows;
- analytics/audit/event pipelines.

Mark each as release-critical, supporting, or non-critical.

### 2.5 Build a risk register

For each surface or journey, score qualitatively:

- business impact;
- user reach;
- privilege level;
- data sensitivity;
- mutation/destructive potential;
- external dependency count;
- concurrency/state complexity;
- implementation churn;
- prior defect history if known.

Use High/Medium/Low or another simple scale. Do not invent numeric precision unless the project already uses one.

## 3. Phase 1 - Environment qualification

### 3.1 Discover native project commands

Inspect project scripts, Makefiles, task runners, CI definitions, Docker/Compose files, READMEs, and package manifests before constructing commands.

Prefer project-native commands because they encode intended configuration.

### 3.2 Avoid gratuitous dependency changes

Do not upgrade frameworks or regenerate lockfiles just to start QA unless the release candidate itself requires the change. Environment repair must not silently become dependency modernization.

### 3.3 Start dependencies safely

Start only the services needed for the tested system. Verify:

- database connectivity;
- cache/queue connectivity;
- storage availability;
- application startup;
- migrations;
- health/readiness;
- frontend/backend connectivity;
- worker/consumer startup when relevant.

### 3.4 Qualify test data

Establish fixtures or accounts for materially different roles. Include data states needed to test:

- new/empty account;
- populated account;
- privileged user;
- restricted user;
- owner vs non-owner object access;
- pending/approved/rejected/expired/cancelled states if the domain uses them;
- boundary-sized records/files where relevant.

Never use real production personal data when synthetic fixtures can prove the behavior.

### 3.5 Prove clean startup

At minimum prove:

1. the application starts;
2. a health/smoke endpoint or equivalent responds;
3. one user-facing flow reaches the backend;
4. one state-changing operation persists or is handled as expected;
5. logs do not show immediate fatal errors.

If startup fails, debug that failure first. Treat it as release-blocking until resolved.

## 4. Phase 2 - QA strategy construction

Use `qa-matrix.md`.

### 4.1 Define release-critical journeys

Identify the minimum journeys without which the product fails its intended release purpose. Include privileged administrative flows if they are necessary to operate the product.

### 4.2 Map roles to journeys

For each journey, identify:

- who may perform it;
- who may view it;
- who must be denied;
- who receives downstream visibility or notifications.

### 4.3 Map state transitions

For every mutable entity, capture valid transitions and invalid transitions. Example:

`draft -> submitted -> approved/rejected -> completed`

Test both accepted and rejected transitions.

### 4.4 Define negative and boundary coverage

For each critical path, add cases for invalid input, repeated input, expired/stale state, partial failure, concurrency when meaningful, unauthorized access, and interrupted navigation.

### 4.5 Define evidence method

Every matrix row should have a planned evidence method, such as:

- automated test command;
- browser/manual execution;
- API request/response;
- database query/state inspection;
- logs/traces;
- combined evidence.

## 5. Phase 3 - Automated baseline

### 5.1 Execute before editing

Run all available project-required checks before making defect fixes. This establishes which failures pre-existed Stage 10 changes.

### 5.2 Record exact command results

For each command record:

- command;
- working directory/package;
- result PASS/FAIL/NOT RUN;
- relevant summary counts;
- failure identifier or log location;
- whether failure is pre-existing.

### 5.3 Classify each failure

Do not immediately modify code. Classify as:

- implementation defect;
- test defect;
- environment/configuration defect;
- flaky/non-deterministic;
- approved requirement changed but test stale;
- external service unavailable.

A broken test is not automatically a product defect, and a broken product must not be excused as a broken test without evidence.

## 6. Phase 4 - Product QA execution waves

Run higher-risk waves first.

### Wave A - Core journeys

For each release-critical journey:

1. reset or establish known preconditions;
2. execute the journey as the intended role;
3. verify visible result;
4. verify persisted/backend result;
5. refresh/reload and verify persistence;
6. verify downstream role/system effects;
7. verify audit/log/notification effects if required;
8. mark the matrix row with evidence.

### Wave B - Permission boundaries

For each protected capability:

- verify allowed role succeeds;
- verify forbidden role is denied at the server/API layer;
- attempt direct route/endpoint access where safe;
- verify owner vs non-owner access;
- verify object ID substitution does not bypass ownership;
- verify stale privilege/session behavior if roles can change.

### Wave C - State and data integrity

Verify valid and invalid transitions, duplicate mutation behavior, transactionality, queue/job side effects, stale cache/UI, and orphan prevention.

### Wave D - Negative and recovery behavior

Exercise invalid, interrupted, duplicate, expired, malformed, slow, and partial-failure conditions. Confirm the system fails safely and gives actionable feedback.

### Wave E - UI quality

Exercise responsive layout, keyboard, focus, error states, modals, tables, long content, RTL/LTR and accessibility requirements.

### Wave F - Security regression

Use `auth-security-regression.md`. Focus on release regressions and known risk boundaries. Do not overclaim this as a penetration test.

### Wave G - Performance/reliability smoke

Use `performance-reliability.md`. Look for obvious regressions that would make the release unusable or unstable.

## 7. Phase 5 - Defect triage

Create a defect record as soon as a meaningful issue is reproducible.

Minimum fields:

- ID;
- title;
- severity;
- priority;
- area;
- environment;
- role;
- preconditions;
- reproduction steps;
- expected;
- actual;
- evidence;
- suspected layer;
- root cause when confirmed;
- fix summary;
- regression coverage;
- status.

Do not assign P0/P1 solely because an issue occurs in a security-related component. Use the impact rubric in `defect-rca-fix-loop.md`.

## 8. Phase 6 - Corrective patch loop

For each defect:

1. Reproduce twice when practical or otherwise establish deterministic evidence.
2. Minimize the scenario.
3. Identify the first layer where observed behavior diverges from expected behavior.
4. Inspect recent/related code and data flow.
5. Form a root-cause hypothesis.
6. Run a focused experiment or inspect evidence that can falsify it.
7. Define a narrow patch boundary.
8. Add/adjust a failing regression test when practical.
9. Apply the fix.
10. Run the focused test.
11. Re-run the original end-to-end reproduction.
12. Run adjacent regression.
13. Update defect status and evidence.

If two fix attempts materially expand scope without converging, stop and re-evaluate the root-cause hypothesis before making a third broad change.

## 9. Phase 7 - Regression and burn-down

### 9.1 Severity-based regression depth

- P0: full critical-path and full project-required suite plus targeted security/data checks.
- P1: targeted reproduction, adjacent module/state/role regression, all critical journeys, full project-required suite.
- P2: targeted reproduction plus adjacent regression; broader suite based on touched layer.
- P3: targeted verification and relevant local regression.

### 9.2 Flaky tests

Never rerun a flaky failure repeatedly until it passes and then report PASS. Record the failed attempts, determine whether the flake is environmental or code-related, and either stabilize it or list it as a known issue with release impact.

### 9.3 Pre-existing failures

Pre-existing does not mean harmless. Assess release impact. A pre-existing P1 is still a blocker.

## 10. Phase 8 - Release-candidate closure

Before closure:

- update every matrix row;
- update every defect status;
- re-run required suites;
- verify P0/P1 count is zero;
- verify all critical journeys have executed evidence;
- verify no serious unresolved authorization/data-integrity issue exists;
- verify known issues are complete;
- evaluate every gate in `quality-gates.md`.

## 11. Phase 9 - Handoff

Prepare Stage 11 with factual notes only:

- release-candidate identity;
- environment used;
- commands that passed;
- residual P2/P3 issues;
- operational concerns Stage 11 must verify without repairing product defects;
- migrations/configuration assumptions;
- external integrations not fully exercised and why.

Do not defer a known release-blocking product defect to Stage 11.

## 12. Conditional branches

### Application cannot start

- Capture exact failure.
- Separate dependency/runtime/configuration issues from product code issues.
- Repair only what belongs to the release candidate or local test harness.
- Re-run startup from a clean state.
- If still impossible, BLOCK Stage 10.

### External sandbox unavailable

- Verify local contract and input/output validation.
- Verify timeout/error/retry/fallback behavior using controlled substitutes.
- Mark live integration as unverified.
- Block only if that live integration is release-critical and cannot be safely inferred.

### Browser automation unavailable

- Use interactive/manual browser tooling if available.
- Keep explicit evidence notes.
- If the release-critical UI cannot be exercised at all, do not claim it passed.

### Database inspection unavailable

- Use API-visible and application-visible evidence where sufficient.
- For critical mutation/integrity claims that require persistence proof, mark verification incomplete if no safe alternative exists.

### Monorepo

- Identify touched packages and dependency graph.
- Run package-local checks first.
- Then run repository-level gates required for the release.

### Multiple frontends or role-specific apps

- Maintain separate matrix sections per app/role.
- Test cross-application effects explicitly.

## 13. Completion discipline

Do not write the final PASS marker until:

1. artifact files exist;
2. report and matrix are internally consistent;
3. artifact validator passes when executable;
4. the mandatory quality gates have been evaluated;
5. no P0/P1 remains open.
