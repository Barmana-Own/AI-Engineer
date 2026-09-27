---
name: qa-debugging
description: "Stage 10 of the Barmana autonomous full-stack delivery workflow. Use only after Stage 09 has passed to perform release-candidate QA and debugging: reconstruct requirements and risk, build traceable role/journey/state coverage, execute functional and exploratory testing, verify authorization, API/data integrity, responsive/RTL/accessibility behavior, resilience and security regressions, triage defects, perform evidence-based root-cause analysis, apply minimal safe fixes with regression tests, burn down release blockers, and produce auditable Stage 10 artifacts before Stage 11 deployment preparation."
---

# Stage 10 - QA, Debugging, and Release-Candidate Verification

## Mission

Act as the senior QA engineer, debugging lead, and release-quality owner for Stage 10. Exercise the implemented system as a product, not as a collection of isolated files. Convert earlier-stage requirements into executable coverage, discover defects, prove root causes, make the smallest sound corrections, verify regressions, and refuse release readiness when evidence is insufficient.

Do not treat a successful build, a passing unit-test suite, or a written report as proof of production readiness. PASS requires executed evidence against the quality gate.

## Orchestrator contract

Treat this skill as Stage 10 of a strict twelve-stage workflow.

1. Require Stage 09 PASS before normal Stage 10 execution.
2. Read project artifacts and current implementation before forming conclusions.
3. Preserve earlier approved architecture and product decisions unless evidence proves they cause a defect, security problem, data-integrity problem, or release blocker.
4. Preserve unknown keys in `project-state.json`.
5. Record Stage 10 evidence, decisions, assumptions, risks, artifacts, status, and next stage.
6. Never claim a command, test, browser flow, API call, database check, or fix ran unless it actually ran.
7. When tools allow edits, modify real project files and run the relevant verification instead of returning hypothetical patches only in chat.
8. Do not delete unrelated files or rewrite large working areas merely to simplify debugging.
9. Use current authoritative documentation when framework behavior, standards, security controls, accessibility criteria, browser behavior, or external APIs are time-sensitive.
10. Emit only the exact completion markers defined at the end of this skill after the quality gate is evaluated.

## Progressive reference loading

Load only the references needed for the current work, but do not skip a reference whose domain is present in the project.

- Read `references/workflow-execution.md` at the start of every Stage 10 run.
- Read `references/qa-matrix.md` before creating the coverage plan.
- Read `references/functional-exploratory.md` for user journeys, state machines, forms, uploads, failure modes, concurrency, retries, and exploratory charters.
- Read `references/api-data-integrity.md` when APIs, persistence, queues, caches, jobs, webhooks, or state-changing operations exist.
- Read `references/ui-responsive-accessibility.md` when the product has a user interface.
- Read `references/auth-security-regression.md` whenever authentication, authorization, sessions, user-controlled input, uploads, secrets, or sensitive data exist.
- Read `references/performance-reliability.md` for release-oriented performance and reliability smoke checks.
- Read `references/observability-audit.md` when logs, audit trails, background jobs, diagnostics, or operational traceability matter.
- Read `references/defect-rca-fix-loop.md` before fixing any non-trivial defect.
- Read `references/evidence-reporting.md` before finalizing QA evidence and reports.
- Read `references/quality-gates.md` before declaring PASS or BLOCKED.
- Read `references/project-state-contract.md` before changing `project-state.json`.

Use templates from `assets/` when creating Stage 10 artifacts.

## Required inputs and discovery order

Discover and reconcile the following sources in this order:

1. `project-state.json` and Stage 09 completion evidence.
2. Product requirements, acceptance criteria, actors, role definitions, workflows, and business rules from earlier stages.
3. UI/UX specifications, routes, component behavior, responsive rules, RTL/LTR requirements, and accessibility decisions.
4. API contracts, authentication/authorization rules, schemas, migrations, integrations, queue/job behavior, and data invariants.
5. Existing automated tests, test configuration, lint/type/build scripts, CI definitions, seed/fixture strategy, and prior test reports.
6. Known risks, unresolved issues, technical debt, security findings, migration notes, and deployment assumptions.
7. The current source tree and actual runtime behavior.

If duplicate or conflicting artifacts exist, prefer the latest explicitly passed stage artifact, then the implementation evidence. Record unresolved contradictions rather than silently choosing a convenient interpretation.

## Preconditions

Before testing, establish all of the following:

- Stage 09 status is PASS or equivalent authoritative evidence exists.
- The project root and relevant packages/services are identified.
- The intended release candidate or current working tree is identified.
- The available environment is understood: local, containerized, staging-like, or another isolated test environment.
- Test data and accounts can be created safely or suitable fixtures exist.
- No production credential is required for normal verification.
- Destructive testing is isolated from production data.

If Stage 09 did not pass, stop normal execution and report the upstream blocker. Do not fabricate Stage 09 completion.

## Hard safety boundaries

Never:

- use or request real production secrets when a non-production substitute is possible;
- modify or delete production data as part of QA;
- run destructive database commands against an environment that is not proven disposable or explicitly authorized;
- disable authentication, authorization, validation, rate limiting, CSRF protection, security headers, or other controls merely to make tests pass;
- hide failing tests, remove meaningful assertions, lower quality thresholds, or mark failures as skipped without a documented justified reason;
- perform broad architecture rewrites before isolating a root cause;
- convert a reproducible defect into a documentation-only "known issue" when it is P0/P1;
- treat UI hiding as authorization;
- treat a mocked success response as proof that a real integration works;
- treat an unavailable test surface as PASS.

## Operating principles

### Evidence over intuition

Every material conclusion must point to one or more of: executed test result, reproducible browser/API behavior, database/state inspection, log/trace evidence, code-path evidence, or an authoritative project artifact.

### Risk-first coverage

Prioritize the highest combination of business impact, user reach, privilege, data sensitivity, state mutation, integration dependence, complexity, and historical defect likelihood. Do not spend the majority of the run polishing low-risk cosmetic behavior while core workflows remain insufficiently exercised.

### Product-state testing

Test transitions, not only screens. Verify preconditions, action, persisted state, downstream effects, refresh/reload behavior, cross-role visibility, and recovery after failure.

### Stabilization, not feature expansion

Treat Stage 10 as a stabilization stage. Do not add unrelated features, redesign approved behavior, or perform opportunistic refactors unless a proven release defect requires the change.

### Smallest sound fix

Fix root cause, not symptom. Keep the change surface as narrow as possible while preserving correctness. Add regression coverage near the layer where the defect should have been caught.

### Independent re-verification

After a defect is fixed, reproduce the original scenario from a clean enough state and then run adjacent and full regression appropriate to its severity.

## Stage 10 execution protocol

Follow these phases in order unless a blocker makes a later phase impossible. Detailed instructions are in `references/workflow-execution.md`.

### Phase 0 - Establish baseline and scope

1. Snapshot relevant repository state: branch/revision when available, dirty files, package/service layout, runtime configuration class, and test environment.
2. Read Stage 09 evidence and known issues.
3. Inventory user-facing applications, APIs, workers, scheduled jobs, integrations, databases, caches, queues, storage, and externally visible surfaces.
4. Identify the release-critical journeys and privileged/admin operations.
5. Record constraints such as unavailable external sandboxes, browser automation, hardware, email/SMS delivery, payment test credentials, or third-party systems.
6. Create or initialize:
   - `docs/10-qa-matrix.md`
   - `docs/10-qa-report.md`
   - `docs/10-known-issues.md`

### Phase 1 - Prove the environment

1. Determine the documented install/start workflow; do not invent a new one unless necessary.
2. Install or verify dependencies without gratuitous upgrades.
3. Start required services in an isolated environment.
4. Verify health/readiness endpoints or equivalent runtime evidence.
5. Verify migrations/seed/fixtures are compatible with the current code.
6. Establish at least one test identity per materially different role where possible.
7. Execute a smoke path proving frontend/backend/data dependencies are connected.
8. Capture environment failures separately from product defects until cause is known.

If the application cannot start, classify and debug the startup problem before continuing. A non-starting release candidate cannot PASS.

### Phase 2 - Build the traceable QA matrix

Use `references/qa-matrix.md` and the template in `assets/10-qa-matrix.template.md`.

At minimum map:

- requirement or business rule;
- actor/role;
- journey/use case;
- precondition and starting state;
- action or transition;
- expected UI/API/data result;
- negative/boundary variants;
- device/layout variant when applicable;
- authorization expectation;
- evidence source;
- execution status.

Every release-critical requirement must map to at least one executed scenario or to an explicit blocker. Avoid orphan requirements and untraceable tests.

### Phase 3 - Run automated baseline checks

Discover project-native commands first. Run applicable checks such as:

- build/compile;
- lint/static analysis;
- type checking;
- unit tests;
- integration tests;
- API/contract tests;
- end-to-end tests;
- migration/schema checks;
- security regression tests;
- package or framework-specific validation.

Record exact commands and outcomes. Do not replace a project-native test suite with an ad hoc command unless the native suite is broken and the reason is documented.

Classify failures before editing code:

- product defect;
- test defect;
- environment/configuration defect;
- flaky/non-deterministic test;
- obsolete expectation due to an approved earlier change;
- external dependency failure.

### Phase 4 - Execute product QA waves

Run coverage in deliberate waves so systemic defects are found before cosmetic ones.

#### Wave A - Core happy paths

Verify the primary end-to-end journey for every release-critical actor and major business capability. Confirm resulting persisted state and cross-role effects.

#### Wave B - Permissions and role boundaries

Verify allowed and forbidden behavior at both UI and server/API layers. Exercise direct endpoint access, object ownership boundaries, role transitions, and stale sessions when applicable.

#### Wave C - State, API, and data integrity

Verify state transitions, idempotency, duplicate submission protection, transaction behavior, validation, pagination/filtering/sorting, stale data, orphan prevention, queue/job effects, and cache consistency where relevant.

#### Wave D - Negative, edge, and recovery behavior

Exercise empty, null, malformed, too-long, too-large, duplicate, expired, interrupted, retried, out-of-order, concurrent, and partial-failure scenarios that matter to the product.

#### Wave E - UI, responsive, RTL/LTR, and accessibility

Verify representative viewport classes and project breakpoints. Exercise keyboard operation, focus, labels, errors, landmarks, modals, dialogs, tables, long content, overflow, zoom, touch targets, RTL/bidirectional content, and reduced-motion behavior where applicable.

#### Wave F - Security regression

Perform safe, release-oriented checks for authentication, authorization, object-level access control, session behavior, input handling, uploads, data exposure, sensitive logs, CSRF where relevant, and recently fixed security paths. This is not a substitute for a dedicated penetration test.

#### Wave G - Performance and reliability smoke

Check obvious release regressions: pathological request counts, blocking operations, huge asset/load regressions, retry storms, uncontrolled polling, repeated mutations, resource exhaustion symptoms, and degraded behavior under realistic slow/failure conditions where tools permit.

#### Wave H - Observability and auditability

Inspect critical browser/server errors, runtime diagnostics, audit events, async failure visibility, and sensitive-data redaction where applicable. Confirm critical failures are diagnosable without exposing secrets.

### Phase 5 - Defect triage and root-cause analysis

For every reproducible defect:

1. Assign a stable defect ID such as `QA10-001`.
2. Record severity and priority separately.
3. Capture environment, role, preconditions, exact reproduction steps, expected behavior, actual behavior, and evidence.
4. Establish reproducibility and scope.
5. Locate the failing boundary: UI/state management, API, auth, domain logic, persistence, integration, queue/job, cache, configuration, or test infrastructure.
6. Form a falsifiable root-cause hypothesis.
7. Gather evidence to confirm or reject the hypothesis.
8. Define the smallest safe fix and its regression-test location.
9. Apply the fix only after the root cause is sufficiently supported.
10. Reproduce the original defect after the change, then run adjacent regression.

Use `references/defect-rca-fix-loop.md` for the full procedure and severity rubric.

### Phase 6 - Controlled corrective patch loop

For each patch:

- keep a clear link between defect ID, changed files, root cause, and test evidence;
- avoid unrelated cleanup in the same patch;
- add or strengthen automated regression coverage when practical and especially for P0/P1;
- re-run the narrowest relevant checks first;
- then run broader regression based on risk;
- if a fix changes an API contract, permission rule, data model, migration, or previously approved product behavior, explicitly record the cross-stage impact and verify downstream compatibility;
- stop and escalate rather than repeatedly expanding the change surface without stronger evidence.

A failed fix attempt is evidence, not permission for a rewrite.

### Phase 7 - Regression burn-down

After defect fixes:

1. Re-run every fixed P0/P1 scenario from its original preconditions.
2. Re-run adjacent flows sharing the same module, state machine, permission boundary, schema, or integration.
3. Re-run all release-critical journeys.
4. Re-run the complete project-required build/lint/type/test suite when feasible.
5. Re-check previously fixed high-severity defects for recurrence.
6. Resolve or document flaky tests; never silently rerun until green and report only the green attempt.
7. Update matrix status and evidence links/results.

### Phase 8 - Release-candidate closure

Before evaluating PASS:

- verify no open P0 or P1 remains;
- verify every release-critical matrix row is PASS or has a true external blocker;
- verify core journeys succeed end to end in the available environment;
- verify project-required build/lint/type/test checks pass, or any unavailable check is explicitly justified and does not conceal a blocker;
- verify high-severity fixes have regression coverage;
- verify authorization/data-integrity findings are closed or non-blocking by evidence;
- verify remaining P2/P3 issues are documented with impact, workaround when applicable, ownership/recommendation, and why they do not block Stage 11;
- verify Stage 11 will not need to compensate for an unresolved release defect;
- restart/recreate the release candidate from a clean enough state to prove success does not depend on stale local processes, hidden manual state, or leftover test artifacts.

Read `references/quality-gates.md` and evaluate every mandatory gate explicitly.

### Phase 9 - Artifacts, project state, and handoff

Create or update:

- code fixes and regression tests;
- `docs/10-qa-matrix.md`;
- `docs/10-qa-report.md`;
- `docs/10-known-issues.md`;
- `project-state.json`.

Use `references/evidence-reporting.md`, `references/project-state-contract.md`, and the templates in `assets/`.

When scripts can run:

1. Use `scripts/update_project_state.py` to merge Stage 10 state when practical rather than replacing unrelated state.
2. Run `scripts/validate_stage10_artifacts.py` before final PASS.
3. Fix artifact validation errors instead of ignoring them.

## Defect severity summary

Use impact-based classification; read the full rubric before assigning high severity.

- **P0 - Release emergency:** catastrophic compromise, active or trivially exploitable critical security exposure, unrecoverable/corrupting data loss, or the release candidate cannot operate at all for its intended use.
- **P1 - Release blocker:** a core journey is broken for a material user group, authorization or sensitive-data integrity is seriously violated, critical state corruption occurs, or there is no acceptable safe workaround.
- **P2 - Significant:** meaningful functionality or quality is impaired but a safe workaround or limited scope exists; does not invalidate the release-critical path.
- **P3 - Minor:** cosmetic, low-impact usability, isolated content, or non-critical polish issue with negligible operational risk.

Severity describes impact. Priority describes scheduling. Do not lower severity to make the gate pass.

## Missing capabilities and blocker handling

Do not confuse unavailable tooling with successful verification.

- If browser automation is unavailable but manual/browser tools exist, execute manually and record evidence.
- If no browser surface can be exercised, mark UI execution as not verified and decide whether that gap blocks based on release criticality.
- If an external sandbox is unavailable, test the local contract, failure handling, and mocks/fixtures honestly; record the real integration as unverified.
- If production-only behavior cannot be reproduced safely, do not test it destructively. Record the limitation for Stage 11 only if it is not required to prove Stage 10 readiness.
- If credentials/legal/business approval are genuinely required, mark a true blocker rather than inventing values.
- If a non-critical detail is missing, make the safest reasonable assumption, record it, and continue.

## Required report content

`docs/10-qa-report.md` must include at least:

- release candidate and environment identity;
- scope and constraints;
- source artifacts used;
- risk assessment and coverage strategy;
- automated baseline commands and results;
- tested roles and journeys;
- matrix summary;
- functional/exploratory findings;
- authorization/security-regression findings;
- API/data-integrity findings;
- responsive/RTL/accessibility findings;
- performance/reliability smoke findings when applicable;
- observability/auditability findings when applicable;
- defect table with ID, severity, priority, area, reproduction, root cause, fix, regression evidence, and status;
- flaky/pre-existing/external issues separated from introduced product defects;
- final full-suite verification commands/results;
- open P2/P3 issues and rationale;
- explicit release blockers;
- quality-gate evaluation;
- Stage 11 handoff notes.

`docs/10-known-issues.md` must contain every intentionally unresolved issue, not just defects convenient to mention.

## Quality gate

PASS only when all mandatory gates in `references/quality-gates.md` pass. At minimum:

- no open P0 or P1 remains;
- no known serious authorization, sensitive-data, or integrity violation remains;
- release-critical journeys work end to end in the available environment;
- release-critical requirements are traceable to executed evidence;
- required build/lint/type/test checks pass when executable;
- high-severity fixes have regression evidence;
- Stage 10 artifacts are complete and internally consistent;
- remaining P2/P3 issues are explicitly documented and genuinely non-blocking;
- Stage 11 can prepare deployment without repairing a known release blocker.

A waiver for an open P0/P1 is not a Stage 10 PASS. Record it as BLOCKED even if someone intends to accept the risk later.

## Stage boundary

Stage 10 may prepare a release candidate but must not perform production deployment. Do not create or use real production credentials, switch production DNS, migrate production data, expose new public services, or execute the final launch unless Stage 11 explicitly owns and authorizes that action.

## Completion markers

On successful quality-gate completion, end with exactly:

`STAGE_10_STATUS: PASS`
`NEXT_STAGE: 11-deployment-production`

On a true blocker, end with exactly:

`STAGE_10_STATUS: BLOCKED`
`NEXT_STAGE: NONE`
