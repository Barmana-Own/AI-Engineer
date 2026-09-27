# Application Use Cases and Ports

## Table of contents

1. Use-case contract
2. Command/query guidance
3. Transaction boundaries
4. Idempotency
5. Concurrency
6. Repository ports
7. External service ports
8. Time, IDs, audit, and feature flags
9. Anti-patterns

## 1. Use-case contract

Every meaningful application use case should have an explicit contract containing:

- name and business purpose;
- actor/request context;
- input shape;
- output/result shape;
- authorization rule;
- syntactic and business validation split;
- preconditions/invariants;
- side effects;
- repository/service ports used;
- transaction boundary;
- idempotency expectation;
- concurrency expectation;
- expected errors;
- audit/event behavior when required;
- tests.

Do not create a separate class/file for trivial behavior merely to satisfy a pattern. Preserve idioms of the chosen stack while maintaining conceptual boundaries.

## 2. Command/query guidance

Treat state-changing operations as commands and read-only operations as queries conceptually, even without adopting CQRS tooling.

Commands should make mutation and transactional semantics explicit.

Queries should avoid mutating domain state. They may use optimized read ports later in Stage 05 if required by performance, but do not design physical read models prematurely.

## 3. Transaction boundaries

Stage 04 must identify transaction boundaries even though Stage 05 implements physical persistence.

For each mutation, state:

- which business changes must commit atomically;
- whether external calls occur inside or outside the transaction boundary conceptually;
- whether an outbox/inbox pattern may be required later;
- what compensation or retry behavior exists if an external dependency fails;
- whether the operation can be safely retried.

Do not hold a future database transaction open across slow remote calls unless a hard requirement justifies it.

When multiple repository mutations form one invariant-preserving operation, expose a unit-of-work/transaction abstraction or otherwise document a Stage 05 atomicity requirement.

## 4. Idempotency

Define idempotency for operations that can be repeated due to network retry, browser resubmission, webhook delivery, queue retry, scheduled jobs, or payment/provider callbacks.

Specify:

- idempotency key source;
- scope (actor/tenant/operation);
- duplicate detection behavior;
- result replay semantics;
- retention window requirement for Stage 05;
- conflict behavior when the same key is reused with different payload meaning.

Do not require idempotency everywhere. Apply it where duplicate execution would cause harm or externally observable inconsistency.

## 5. Concurrency

Identify races such as:

- two approvals of the same request;
- inventory/resource allocation;
- double payment/capture;
- duplicate membership/invite;
- state transition from stale data;
- concurrent edits where overwrite is unsafe.

Document whether Stage 05 needs:

- uniqueness constraint;
- optimistic concurrency/version check;
- compare-and-set semantics;
- serialized allocation;
- advisory/distributed lock only when genuinely necessary.

Prefer database-enforceable invariants over best-effort application checks when Stage 05 can support them.

## 6. Repository ports

Design repository ports from use-case needs, not table CRUD.

Good examples:

- `findActiveSubscriptionForAccount(accountId)`
- `saveOrder(order)`
- `reserveUniqueExternalReference(reference, ...)`
- `listPendingApprovals(filter, page)`

Weak default examples:

- `getAll()`
- `update(any)`
- generic repository interfaces that erase domain semantics.

A port should define:

- semantic operation;
- required consistency;
- not-found behavior;
- pagination/order semantics when relevant;
- tenant scoping;
- error categories that application logic needs;
- transaction participation expectations.

## 7. External service ports

Wrap remote providers behind application-owned interfaces.

For each port define:

- operation and semantic inputs/outputs;
- timeout expectation;
- retry eligibility;
- idempotency expectation;
- error classification (`temporary`, `permanent`, `rate_limited`, `auth_failure`, etc.);
- sensitive fields/redaction;
- correlation/tracing context;
- provider-specific mapping location.

Keep provider SDK/request/response types inside infrastructure adapters.

## 8. Time, IDs, audit, and feature flags

Abstract time when business rules depend on current time and deterministic tests benefit from a clock.

Abstract ID generation when IDs are created by application/domain behavior before persistence or deterministic tests need control.

Define an audit port when the product requires non-repudiation, traceability, regulated change history, or privileged-action logging.

Use feature-flag abstraction only when feature flags already exist or validated rollout requirements demand them.

## 9. Anti-patterns

Do not:

- put authorization only in controllers;
- return raw ORM models from application use cases;
- make domain logic call network services directly;
- let a generic repository expose arbitrary query builders to application logic;
- use retries to mask permanent validation/business failures;
- implement distributed locks before proving a concurrency need;
- make every read path instantiate full domain aggregates when a focused query contract is more appropriate.
