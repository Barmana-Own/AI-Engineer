# Defect Triage, Root-Cause Analysis, and Corrective Fix Loop

## Table of contents

1. Defect lifecycle
2. Defect record
3. Severity rubric
4. Priority rubric
5. Reproduction discipline
6. Layer isolation
7. Root-cause method
8. Patch boundary
9. Regression design
10. Flaky failures
11. Pre-existing defects
12. Failed fix attempts
13. Architecture-change threshold
14. Closure criteria

## 1. Defect lifecycle

Use this lifecycle:

`Observed -> Reproduced -> Triaged -> Root cause confirmed -> Fix planned -> Fixed -> Regression verified -> Closed`

Alternative terminal statuses:

- `Known issue - non-blocking`
- `Blocked - external dependency`
- `Not a defect - expected behavior`, with evidence
- `Duplicate`, linked to canonical defect

Do not jump directly from Observed to Fixed without preserving enough evidence to prove what changed.

## 2. Defect record

Use stable IDs such as `QA10-001`.

Record:

- title;
- severity P0-P3;
- priority;
- affected requirement/matrix row;
- module/surface;
- environment/revision;
- role/account class;
- preconditions/data state;
- exact reproduction steps;
- reproducibility rate if intermittent;
- expected result;
- actual result;
- visible/API/data/log evidence;
- first known bad boundary/layer;
- root cause;
- affected files/components;
- fix summary;
- regression test/evidence;
- adjacent regression performed;
- final status.

## 3. Severity rubric

Severity measures impact, not inconvenience to the tester.

### P0 - Release emergency

Use when one or more applies and evidence supports catastrophic scope:

- release candidate cannot start or operate at all for intended use with no viable safe workaround;
- unrecoverable or widespread corruption/destruction of critical data;
- trivially exploitable critical security condition with catastrophic impact, such as broad system/admin compromise or equivalent severe exposure;
- irreversible critical business effect occurring broadly and uncontrollably.

Do not use P0 merely because the word "security" or "data" appears in the defect.

### P1 - Release blocker

Use when:

- a release-critical journey is broken for a material user/role;
- serious authorization bypass exposes or changes sensitive/privileged data;
- critical state/integrity violation can occur in normal or plausible use;
- payment/order/approval/identity-like core mutation is unsafe;
- a major accessibility/UI defect makes a core journey unusable for a required audience;
- no acceptable safe workaround exists.

### P2 - Significant

Use when:

- meaningful functionality is wrong or degraded;
- impact is limited to a smaller surface or less critical path;
- safe workaround exists;
- data/security impact is bounded and non-critical;
- substantial usability/responsive/accessibility issue exists without blocking release-critical operation.

### P3 - Minor

Use for:

- cosmetic/polish defects;
- minor copy/alignment issues;
- isolated low-impact usability issues;
- non-critical visual inconsistency;
- low-risk technical issue with negligible release impact.

### Severity dimensions

When uncertain, evaluate:

- business impact;
- data sensitivity/integrity;
- privilege impact;
- affected population;
- reproducibility;
- exploitability;
- recoverability;
- workaround safety;
- core-journey dependency.

Document the rationale for P0/P1.

## 4. Priority rubric

Priority answers "when should this be fixed?" and may differ from severity.

Suggested:

- `Immediate` - active release blocker or blocks further QA;
- `Before Stage 10 closure` - must be fixed for PASS;
- `Before production launch if owner accepts Stage 10 non-blocking classification` - generally P2 operational issues;
- `Backlog` - low-impact P3.

Never lower severity because schedule pressure exists.

## 5. Reproduction discipline

Before changing code:

1. Reproduce from documented preconditions.
2. Confirm the expected behavior from authoritative requirement or domain rule.
3. Reduce the scenario to the smallest reliable sequence.
4. Test one relevant variant to determine scope.
5. Capture evidence.

If intermittent, record attempts and success rate rather than presenting it as deterministic.

## 6. Layer isolation

Trace from symptom toward source.

### UI/state layer

Check:

- event handler fired;
- local/form state;
- validation;
- request construction;
- stale cache/state;
- render condition;
- route lifecycle.

### API/controller layer

Check:

- route selected;
- auth middleware;
- request parsing;
- validation;
- handler branch;
- response mapping.

### Domain/service layer

Check:

- business rule;
- state transition;
- permissions;
- calculation;
- idempotency;
- error mapping.

### Persistence layer

Check:

- query/transaction;
- uniqueness/constraints;
- stale row/version;
- migration/schema mismatch;
- commit/rollback;
- orphan state.

### Integration/async layer

Check:

- outbound request/event;
- timeout/retry;
- response/event mapping;
- queue delivery;
- webhook order/replay;
- cache invalidation.

Locate the first layer where actual behavior diverges from expected behavior.

## 7. Root-cause method

Write a falsifiable hypothesis, for example:

"The second product image disappears after approval because the approval serializer reads the legacy two-item relation rather than the current media collection."

Then seek evidence that could disprove it.

Useful techniques:

- inspect request/response at each boundary;
- inspect persisted state before/after;
- inspect logs/traces;
- run a focused test around the suspected function;
- compare working and failing data;
- inspect recent change/diff where available;
- temporarily instrument in a non-production environment, then remove unnecessary debug instrumentation.

A guess is not a root cause.

## 8. Patch boundary

Before editing, state:

- defect ID;
- root cause;
- files/layers expected to change;
- expected invariant after fix;
- regression test location;
- likely adjacent risk.

Prefer the smallest change that restores the intended invariant.

Avoid:

- unrelated refactors;
- framework upgrades;
- broad renaming;
- disabling validation;
- relaxing auth;
- removing tests;
- changing requirements to match the bug.

## 9. Regression design

Regression should fail before the fix or otherwise prove the exact broken behavior, then pass after the fix.

Place it at the lowest layer that would reliably prevent recurrence while preserving at least one end-to-end re-verification for P0/P1.

Examples:

- serializer bug -> service/API test plus critical UI recheck;
- permission bug -> authorization integration test across allowed/forbidden roles;
- state transition bug -> domain/integration test for valid and invalid transitions;
- duplicate submission -> idempotency/integration test plus repeated user action;
- layout defect -> targeted UI/E2E or repeatable visual/manual check depending tools.

## 10. Flaky failures

A flaky failure has variable outcomes under materially identical conditions.

Procedure:

1. Preserve at least one failing output.
2. Repeat a limited number of controlled attempts.
3. Identify timing/order/shared-state/external dependency causes.
4. Stabilize production code or test harness according to root cause.
5. Do not hide the test with unconditional skip/retry.
6. Document residual flakiness as a reliability risk.

A retry mechanism in CI can complement, but not substitute for, root-cause work on meaningful flakes.

## 11. Pre-existing defects

Tag a defect as pre-existing only when baseline evidence predates Stage 10 edits or history supports it.

Then assess normally. Pre-existing P0/P1 still blocks Stage 10.

Do not use "pre-existing" as a reason to omit the defect from the report.

## 12. Failed fix attempts

After a failed attempt:

- revert or cleanly supersede the ineffective change when safe;
- update the hypothesis based on new evidence;
- shrink the reproduction further;
- inspect adjacent boundaries.

If two attempts broaden the patch without solving the defect, stop and reassess before a third broad attempt. Avoid uncontrolled patch accumulation.

## 13. Architecture-change threshold

Escalate beyond a local fix only if evidence shows:

- the existing architecture makes the required invariant impossible;
- the defect is systemic across multiple flows;
- repeated local fixes create inconsistent rules;
- a security/integrity boundary is fundamentally misplaced.

If an architectural correction is required, document the earlier-stage decision impacted and re-run broader regression.

## 14. Closure criteria

Close a defect only when:

- original reproduction no longer fails;
- expected behavior is proven;
- regression coverage exists when practical and required by severity;
- adjacent behavior remains valid;
- no new error is hidden by the patch;
- report and matrix status are updated.
