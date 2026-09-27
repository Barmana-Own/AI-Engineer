# Security Testing and Verification Discipline

## Table of contents

1. Test pyramid for Stage 08
2. Test-first security invariants
3. Authorization tests
4. Stateful/business tests
5. Input/output tests
6. Integration/webhook tests
7. Dependency/config checks
8. Retest protocol
9. Regression protocol
10. Handling unavailable tests

## 1. Test pyramid for Stage 08

Use the cheapest deterministic layer that proves the security invariant:

1. pure unit/policy test;
2. service/domain test;
3. database-integrated test;
4. HTTP/API integration test;
5. local end-to-end test;
6. authorized remote test only when environment behavior matters.

Do not prefer a live exploit when a deterministic test proves the same defect safely.

## 2. Test-first security invariants

A good security regression test states who must be denied/allowed, which object/action is protected, and what side effects must not occur.

Prefer assertions on both response and persisted state. For background jobs, assert enqueue/processing side effects as appropriate.

## 3. Authorization tests

For each material protected resource, include representative negative cases:

- unauthenticated;
- wrong user/owner;
- wrong tenant;
- wrong role/function;
- protected field mutation;
- revoked/suspended identity where relevant.

Also keep positive cases for legitimate users so a hardening change does not simply block everyone.

## 4. Stateful and business tests

Test invalid transitions, duplicate/replayed actions, stale objects and small deterministic concurrency scenarios for one-time state. Assert database constraints/transactions where they form part of the invariant.

Do not perform high-volume race/load testing by default.

## 5. Input/output tests

Use representative safe strings/fixtures that exercise parser boundaries without harmful external effects. Test encoded/alternate forms only when they map to a specific bypass hypothesis.

Avoid giant payloads and resource-exhaustion fuzzing.

## 6. Integration and webhook tests

Use local fixtures/known test secrets for signature verification. Test invalid signature, stale timestamp if protocol supports it, duplicate event ID and wrong object/account binding. Never copy a production webhook secret into tests.

## 7. Dependency and configuration checks

Record audit/build/config commands as executed evidence. Tests that rely on network availability must be marked accurately when network failure prevents them.

Configuration tests can validate production mode, required secrets, route mounting and policy wiring without connecting to production.

## 8. Retest protocol

For every fixed Critical/High/Medium finding:

1. rerun the exact failing security regression test;
2. re-read the changed enforcement code;
3. rerun the minimal original reproduction condition;
4. run a legitimate positive case;
5. update ledger `retest` with command/test name and outcome;
6. only then set `status=FIXED`.

A code review alone is not sufficient retest when an executable test can be created reasonably.

## 9. Regression protocol

After targeted fixes, run the project's broader relevant checks:

- unit/integration suites;
- lint/typecheck;
- build;
- migrations if touched;
- security scans/audits used during discovery.

If the suite contains pre-existing failures, distinguish them with baseline evidence. Stage 08 must not introduce new unresolved failures.

## 10. Handling unavailable tests

If a required environment cannot run:

- attempt a local/mocked equivalent;
- write the regression test even if an external dependency prevents execution;
- mark execution `NOT_RUN` with exact reason;
- decide whether the missing execution is compatible with PASS using risk and quality-gate rules.

A Critical/High fix that cannot be meaningfully verified due to a genuine external dependency generally prevents PASS and may be BLOCKED.
