# Change Impact Analysis and Advanced Confidence Techniques

## Purpose

Use advanced techniques selectively where ordinary example-based tests leave material uncertainty. Start from actual code/config/schema changes and risk, not from a desire to use sophisticated tools.

## Table of contents

1. Change-impact analysis
2. Diff-focused risk expansion
3. Contract drift and backward compatibility
4. Property-based testing
5. Mutation testing
6. Safe fuzzing
7. Differential/metamorphic testing
8. Performance and resource smoke checks
9. Feature flags and compatibility modes
10. Async/eventual consistency
11. Network isolation and side-effect containment
12. Test data privacy
13. When to stop

## 1. Change-impact analysis

Before finalizing the risk matrix, inspect the current implementation delta when version-control evidence is available.

Identify changes to:
- auth/session/permission code;
- API routes/controllers/schemas;
- domain/business rules;
- repositories/queries;
- database migrations;
- queues/jobs/events;
- external adapters;
- frontend critical workflows;
- dependency versions;
- configuration/environment behavior;
- feature flags;
- serialization/date/locale logic.

Do not assume a small line diff is low risk. A one-line permission or SQL predicate change can be P0.

Do not treat generated lockfile churn as product behavior without checking the actual dependency change.

## 2. Diff-focused risk expansion

For each materially changed area ask:
1. What behavior could change intentionally?
2. What adjacent behavior could regress unintentionally?
3. What state/data created by an earlier version must still work?
4. What authorization boundary can be widened accidentally?
5. What failure/retry path is affected?
6. What existing test should fail if the change is wrong?

If a high-risk changed line has no credible test path, add it to the matrix even when no explicit requirement ID originally mentioned the implementation detail.

Use diff coverage as a signal when the project supports it, not as a standalone gate.

## 3. Contract drift and backward compatibility

When APIs/events/schemas are consumed by other components or external clients, test compatibility obligations defined by the project.

Check as applicable:
- removed/renamed response fields;
- changed field type/nullability;
- changed enum values;
- changed error/status semantics;
- required request fields newly introduced;
- event schema changes;
- database data readable after migration;
- old client/session/token behavior if compatibility is promised;
- versioned endpoint behavior.

If an OpenAPI/JSON Schema/GraphQL/protobuf/event schema is authoritative, validate implementation or representative responses against it when project tooling supports that validation.

Do not invent backward compatibility requirements that the project explicitly does not promise.

## 4. Property-based testing

Use property-based testing when the domain has broad input space and stable invariants.

Good candidates:
- parsers/formatters;
- money/rounding calculations;
- date range logic;
- state transition constraints;
- validators;
- serialization round trips;
- sorting/pagination invariants;
- allocation/distribution rules.

Examples of properties:
- encode → decode preserves allowed value;
- total allocation never exceeds available amount;
- unauthorized actor can never transition protected state;
- normalized result is idempotent when normalization is part of the contract;
- sorting remains ordered for arbitrary valid inputs.

Requirements:
- keep generated input bounded and valid for the intended domain;
- preserve/replay failing seeds/examples;
- do not let randomness make the suite irreproducible;
- shrink/minimize failing cases when the framework supports it.

Do not add a property-testing library solely for novelty when a concise table-driven test proves the risk adequately.

## 5. Mutation testing

Use mutation testing selectively for high-value pure/domain logic when:
- the project already supports a mutation tool, or adding it is low-risk and justified;
- assertions may be superficially green despite weak behavior checks;
- P0/P1 calculation/permission/state-machine logic deserves stronger confidence.

Use mutation results to identify weak tests, not as a universal percentage target.

Investigate surviving mutants in critical logic:
- missing boundary assertion;
- missing negative path;
- overly broad mocks;
- assertion not observing the actual result.

Do not run expensive repository-wide mutation campaigns by default.

## 6. Safe fuzzing

Use bounded fuzzing for parsers, validators, protocol handlers, upload metadata, or other input-heavy boundaries when it can run locally without offensive side effects.

Rules:
- use test/sandbox targets only;
- bound payload size, iterations, and runtime;
- never target third-party/public systems;
- preserve reproducer input for every crash/failure;
- convert meaningful discovered failures into deterministic regression tests;
- avoid generating dangerous executable payloads when benign malformed input proves the defensive requirement.

Stage 09 fuzzing is correctness/resilience testing, not penetration testing.

## 7. Differential and metamorphic testing

Use when there are two trustworthy ways to evaluate equivalent behavior.

Examples:
- old vs new calculation implementation during migration;
- API response vs direct domain calculation;
- serializer round-trip;
- database query vs in-memory reference for bounded datasets;
- two implementations intended to be equivalent during refactor.

Define the equivalence domain carefully. Do not canonize a known-buggy legacy implementation as the oracle.

Metamorphic examples:
- reordering independent inputs does not change aggregate result;
- adding zero-value item does not change total;
- retrying an idempotent request preserves the same effect.

## 8. Performance and resource smoke checks

Stage 09 is not full load/performance engineering, but automate narrow performance/resource checks when a documented NFR or regression risk exists.

Good targets:
- accidental N+1 query in a critical endpoint;
- unbounded pagination;
- algorithmic regression in critical calculation;
- memory/file handle leak in repeated operation;
- startup/test timeout caused by a new change.

Use stable relative/structural assertions when possible:
- query count under a defined fixture;
- bounded result size;
- no leaked handles;
- operation completes within a generous regression ceiling in a controlled environment.

Avoid brittle millisecond thresholds on noisy developer hardware unless the environment is controlled and the requirement explicitly needs it.

Full load, soak, scalability, and capacity validation belong to a dedicated performance stage/process if the workflow defines one.

## 9. Feature flags and compatibility modes

When critical behavior is gated:
- test flag OFF;
- test flag ON;
- test default state;
- test unauthorized users cannot manipulate server-side flag behavior;
- test data compatibility across state changes if specified;
- test stale clients where compatibility is promised.

Do not only test the currently enabled branch.

## 10. Async and eventual consistency

For event-driven flows:
- assert eventual result with bounded condition polling, not fixed sleep;
- test duplicate event delivery;
- test out-of-order event only when architecture permits it;
- test retry/dead-letter semantics where implemented;
- correlate by stable event/entity IDs;
- clean queues/topics between tests or use isolated namespaces.

Record the maximum wait condition and why it is safe.

## 11. Network isolation and side-effect containment

When tooling permits, prevent routine tests from reaching arbitrary external networks.

Strategies:
- mock/route external HTTP at adapter boundary;
- block unexpected outbound connections in test runner/container;
- allowlist known local/sandbox endpoints;
- fake email/SMS/webhooks;
- use payment/provider sandbox.

A test that unexpectedly reaches the public internet should fail loudly rather than silently creating side effects.

Do not break tests that intentionally validate an approved private sandbox contract; document those separately.

## 12. Test data privacy

Use synthetic or properly anonymized fixtures.

Never commit:
- real customer records;
- real access tokens;
- production database extracts containing PII/secrets;
- private documents/images from users;
- credentials copied from `.env` or logs.

If a production-shaped fixture is necessary, construct a minimal synthetic equivalent preserving only structural characteristics relevant to the bug.

Sanitize failure artifacts, screenshots, HAR files, snapshots, and logs before retaining them.

## 13. When to stop

Advanced techniques are justified only when they reduce material uncertainty.

Stop adding test sophistication when:
- P0/P1 risks already have strong evidence;
- the additional technique duplicates existing confidence;
- infrastructure cost exceeds the risk reduction;
- the technique introduces more nondeterminism than value;
- the work crosses into another stage's responsibility.

Document intentionally deferred P2/P3 advanced testing rather than inflating Stage 09 scope indefinitely.
