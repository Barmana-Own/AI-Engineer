# Execution, Failure Classification, Defect Repair, and Flakiness Policy

## Purpose

Define the disciplined loop between a failing test and a trustworthy Stage 09 conclusion.

## Table of contents

1. Execution order
2. Command evidence
3. Failure classification
4. Product defect loop
5. Test defect loop
6. Test infrastructure/environment defects
7. Specification conflicts
8. Flakiness diagnosis
9. Flakiness acceptance policy
10. Timeouts and hanging tests
11. Scope control
12. Rerun requirements

## 1. Execution order

Run fast/high-signal checks before expensive broad suites.

Recommended order:
1. test configuration/import discovery;
2. targeted new/changed tests;
3. unit suites;
4. integration/database suites;
5. API/contract suites;
6. security regression suites;
7. frontend component suites;
8. E2E/browser suites;
9. canonical full/CI-equivalent suite;
10. coverage collection.

When a prerequisite suite fails catastrophically, diagnose it before wasting time on dependent suites.

Do not stop permanently after the first fix; rerun broad relevant suites before finalizing.

## 2. Command evidence

For each material command record:
- command ID;
- exact command;
- working directory;
- environment classification;
- exit code;
- pass/fail/skipped counts if emitted;
- duration if available;
- purpose;
- log/evidence path if one is produced.

Do not paste secrets or full noisy logs into the report. Summarize and reference sanitized logs if retained.

## 3. Failure classification

Classify before editing.

### `PRODUCT_DEFECT`

Use when the implementation violates a valid requirement/contract/invariant and the test correctly exposes it.

### `TEST_DEFECT`

Use when the test has a bad expectation, bad setup, stale fixture, invalid mock, race introduced by the test, or assertion unrelated to the requirement.

### `TEST_INFRA_DEFECT`

Use when harness/setup tooling is broken: missing test service, bad config, incompatible runner setup, fixture bootstrapping failure.

### `ENVIRONMENT_DEFECT`

Use when the environment differs from supported assumptions: wrong runtime, unavailable container engine, port conflict, filesystem permission, missing browser binary.

### `SPEC_CONFLICT`

Use when two authoritative sources or requirement vs accepted design contradict each other and expected behavior cannot be resolved safely.

### `FLAKY_SUSPECT`

Use when identical conditions yield inconsistent outcomes or timing/order/shared-state symptoms are present.

### `EXTERNAL_DEPENDENCY_BLOCKER`

Use when a required private sandbox/API/credential/service is unavailable and cannot be replaced without invalidating the behavior under test.

### `UNKNOWN`

Temporary only. Investigate until reclassified before final gate unless the issue truly blocks evidence and is recorded as blocker.

## 4. Product defect loop

For a confirmed product defect:

1. Create/minimize a reproducible failing test.
2. Link it to the source requirement/risk and assign defect ID.
3. Verify failure on current implementation.
4. Inspect root cause narrowly.
5. Make the smallest safe implementation change.
6. Run the regression test and confirm it now passes.
7. Run nearby tests in the same module/service.
8. Run the relevant integration/API/E2E suite depending on blast radius.
9. Run the canonical/full suite before final PASS where runnable.
10. Record defect, root cause, files changed, and evidence.

Do not "fix" by weakening the assertion unless the original expectation was proven invalid.

## 5. Test defect loop

When the test is wrong:
1. explain why the expectation/setup is invalid;
2. correct the test/fixture;
3. ensure the revised test still proves the requirement;
4. rerun it repeatedly if nondeterminism was involved;
5. rerun related suites.

Avoid rewriting a test around the current implementation when the requirement says otherwise.

## 6. Test infrastructure/environment defects

Repair narrow test infrastructure when it is part of making Stage 09 reproducible.

Examples:
- missing test DB setup;
- test env file template;
- CI service container config;
- browser install step already implied by project tooling;
- teardown leak;
- port collision strategy.

Do not convert Stage 09 into a production infrastructure redesign.

If a critical dependency cannot be safely supplied, record blocker rather than faking success.

## 7. Specification conflicts

Resolution order:
1. explicit current requirement/acceptance criterion;
2. approved API/security/data contract;
3. prior-stage recorded decision;
4. established behavior represented by authoritative tests/docs;
5. implementation code only as evidence, not sole authority.

If conflict affects P0/P1 behavior and cannot be resolved safely, block downstream progression.

For non-critical ambiguity, choose the safest reasonable interpretation, record it, and continue.

## 8. Flakiness diagnosis

Signals:
- pass/fail changes with no code/config change;
- test passes alone but fails in suite;
- order-dependent failure;
- arbitrary sleeps;
- network/live service dependence;
- shared mutable database/user/session;
- random seed not controlled;
- time boundary;
- async event not awaited;
- fixed port collision;
- cleanup races;
- parallel worker collision.

Diagnostic sequence:
1. run failing test alone;
2. rerun same test at least 3 times;
3. run with immediate neighbors/related suite;
4. vary order or parallelism if supported;
5. inspect clock/random/shared state;
6. inspect external network dependency;
7. inspect setup/teardown leaks;
8. fix root cause;
9. prove 3 consecutive passes after fix;
10. run related suite again.

For high-risk concurrency/E2E flakiness, use more repetitions if practical.

## 9. Flakiness acceptance policy

No known flaky P0/P1 test may remain silently accepted at PASS.

Do not use:
- unconditional retry as the primary fix;
- `skip`;
- quarantine;
- enlarged timeout;
- weaker assertion;
- serial-only execution
as a substitute for root-cause correction unless the project explicitly accepts the limitation and equivalent risk evidence exists.

If a non-critical flaky test cannot be repaired within Stage 09 scope, document it as unresolved and evaluate whether it blocks the full-suite gate. Do not hide it.

## 10. Timeouts and hanging tests

When a test hangs:
- identify open handles/processes;
- verify async work is awaited;
- terminate child processes in teardown;
- close DB/queue/cache clients;
- check browser context/page cleanup;
- check fake timers;
- check deadlock/lock waits.

Do not simply multiply global timeouts without root-cause evidence.

## 11. Scope control

Allowed implementation changes:
- bug fix directly proven by a valid failing test;
- narrow testability seam that does not change product behavior;
- test infrastructure required for reproducibility;
- missing validation/constraint required by a proven requirement.

Escalate/defer:
- broad architecture migration;
- unrelated refactor;
- large UI redesign;
- new feature;
- unrelated dependency modernization;
- release/deployment redesign.

## 12. Rerun requirements

Before declaring a repaired defect resolved:
- regression test passes;
- directly related suite passes;
- affected integration boundary passes;
- full relevant/canonical suite passes when runnable.

Before final Stage 09 PASS:
- no required suite is left red;
- no critical suite is unexecuted without equivalent evidence;
- summary reflects final rerun, not an earlier partial run.
