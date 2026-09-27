# Test Design, Fixtures, and Determinism

## Purpose

Define how tests must be written so they provide durable evidence rather than brittle green output.

## Table of contents

1. Test case anatomy
2. Assertion quality
3. Factories and fixtures
4. Isolation and cleanup
5. Time, randomness, locale, and IDs
6. Mocking policy
7. External boundaries
8. Parallel execution
9. Error and recovery testing
10. Test readability and maintenance
11. Anti-patterns

## 1. Test case anatomy

Each material test should make clear:
- the behavior under test;
- the setup/preconditions;
- the action;
- the observable outcome;
- the safety invariant when failure occurs.

Prefer Given/When/Then or Arrange/Act/Assert structure where it improves clarity.

Use names that describe behavior, not implementation details.

Good:
`rejects update when authenticated user does not own the invoice`

Weak:
`test update 3`

## 2. Assertion quality

Assert the outcome that matters.

Prefer:
- exact business result;
- exact status/error code where contractually stable;
- durable state change;
- absence of forbidden state change;
- correct emitted event/side effect;
- correct transaction rollback;
- correct ownership/tenant scope.

Avoid only asserting:
- `truthy` when exact value matters;
- HTTP 200 without response semantics;
- "function called" when real outcome matters;
- snapshots for dynamic/large objects when targeted assertions are clearer.

For negative tests, assert both rejection and absence of unsafe side effects.

## 3. Factories and fixtures

Use factories/builders to express relevant differences without giant shared fixtures.

A good factory:
- produces valid defaults;
- allows explicit overrides;
- creates only required data;
- avoids hidden global state;
- makes ownership/tenant relationships explicit;
- supports deterministic IDs when needed.

Avoid one enormous seed fixture that every test mutates.

Use fixture scopes deliberately. Shared fixture performance is not worth cross-test contamination.

## 4. Isolation and cleanup

Every test must be runnable independently unless the framework explicitly defines a controlled scenario sequence.

Preferred isolation approaches:
- transaction rollback per test;
- schema/database reset;
- disposable container/database;
- namespace/tenant isolation with deterministic cleanup;
- temp directories.

Do not rely on alphabetical execution order.

When cleanup fails, surface the failure. Silent cleanup errors can invalidate later tests.

## 5. Time, randomness, locale, and IDs

Control sources of nondeterminism.

### Time

When logic depends on time:
- inject/freeze a clock;
- set timezone explicitly;
- test DST/date-boundary behavior if relevant;
- avoid assertions against wall-clock timing unless performance is the subject.

### Randomness

Use fixed seeds or deterministic generators.

Record a generated seed when fuzz/property testing finds a failure so it can be replayed.

### Locale/Unicode

For multilingual/RTL systems, include relevant samples for:
- Persian/Arabic characters;
- normalization-sensitive input when contract specifies behavior;
- mixed RTL/LTR text;
- locale-specific numerals/date formatting where application logic handles them.

Do not normalize user data in tests unless production contract requires that normalization.

### IDs

Avoid hard-coded globally colliding IDs when tests run in parallel. Use unique deterministic prefixes or factory-generated identifiers.

## 6. Mocking policy

Mock a boundary, not the behavior being proven.

Good mocking targets:
- payment provider network call;
- email/SMS provider;
- external government API;
- clock;
- randomness source;
- cloud storage SDK when adapter contract is separately integrated.

Poor mocking targets:
- repository in a test claiming to prove database constraints;
- auth middleware in a test claiming to prove authorization;
- serializer in a contract test;
- every internal service in an integration test.

If a mock reproduces complex third-party semantics, consider a contract fixture/mock server or provider sandbox instead.

## 7. External boundaries

Routine tests must not depend on flaky live third-party services.

Use one of:
- provider sandbox;
- local emulator;
- contract fixtures captured/curated safely;
- mock server with schema-valid behavior;
- adapter fake.

Also test external failure modes:
- timeout;
- 429/rate limit;
- 5xx;
- malformed response where defensive parsing is expected;
- duplicate callback;
- delayed callback;
- partial success.

Do not place real secrets in fixtures.

## 8. Parallel execution

If the suite supports parallel workers:
- avoid fixed shared ports;
- allocate unique DB/schema/tenant/queue namespaces;
- avoid shared mutable temp paths;
- ensure factories generate unique keys;
- isolate browser users/sessions;
- make cleanup worker-safe.

Run a representative parallel mode if CI uses it.

A suite that only passes serially while CI runs parallel is not healthy.

## 9. Error and recovery testing

For critical write operations, test failure atomicity.

Examples:
- DB write 2 fails after write 1;
- queue publish fails after transaction;
- external provider times out;
- duplicate request arrives;
- retry occurs after ambiguous response;
- optimistic lock/version conflict occurs.

Assert whether the contract expects:
- rollback;
- outbox/retry;
- idempotent success;
- explicit recoverable error;
- compensation.

Do not merely assert an exception was thrown.

## 10. Test readability and maintenance

Keep tests close to project conventions.

Prefer:
- small helper functions;
- domain-specific fixture builders;
- clear stable IDs;
- minimal setup;
- meaningful assertion messages where useful;
- comments explaining unusual risk, not restating code.

A future engineer should be able to identify what requirement failed from the test name and traceability ID.

## 11. Anti-patterns

Reject or repair these patterns:
- sleeps used instead of condition-based waits;
- test order dependency;
- random data without replay seed;
- tests that call production services;
- shared mutable singleton fixture;
- giant snapshot with little semantic meaning;
- assertions removed after failure;
- catch-and-ignore around assertions;
- unconditional retries hiding race conditions;
- `skip`/`todo` on critical tests without blocker evidence;
- test named "integration" while all real dependencies are mocked;
- cleanup that truncates a shared non-test database;
- broad mocks that make the tested path impossible in production.
