# Non-Functional Release Review

Non-functional requirements are release requirements when they are approved, security-critical, or necessary for safe operation. Do not invent arbitrary enterprise requirements for a small project, but do not ignore explicit NFRs.

## Performance and capacity

When performance matters:
- identify stated latency/throughput/concurrency budgets;
- detect N+1 queries, unbounded list/export operations, missing pagination and obvious full-table hot paths;
- verify expensive jobs are bounded/queued when architecture expects it;
- inspect payload/image/bundle behavior that makes a critical UI unusable;
- run repository-defined benchmarks/load tests when available;
- avoid claiming capacity from a single local request.

A performance issue blocks when it violates an approved release threshold or makes a core journey practically unusable under expected load.

## Reliability and failure handling

Inspect:
- timeout behavior;
- retries with backoff/jitter where appropriate;
- retry safety/idempotency;
- circuit-breaking or failure isolation where architecture requires it;
- queue retry/dead-letter handling;
- partial external-service failure;
- duplicate webhook/event delivery;
- graceful degradation versus silent data loss;
- scheduled job overlap/locking where applicable.

## Concurrency and consistency

For critical mutations assess:
- duplicate submission;
- optimistic/pessimistic locking where needed;
- transaction boundaries;
- race conditions around quotas/inventory/balances/status transitions;
- idempotency keys for retried external requests;
- stale writes.

## Accessibility

For user-facing core journeys, verify proportional basics:
- keyboard reachability;
- labels/names for form controls;
- visible focus;
- readable error association;
- semantic buttons/links;
- contrast/legibility where obvious;
- dialogs/focus traps where used.

If formal WCAG conformance is an approved requirement, test against that target explicitly rather than claiming compliance from spot checks.

## Internationalization and locale

When multilingual/RTL/localized behavior is in scope, verify:
- direction switching RTL/LTR;
- locale-aware dates/numbers/currency;
- timezone boundaries;
- translated validation/errors;
- layout resilience to text expansion;
- backend storage remains locale-neutral where appropriate;
- URLs/API identifiers do not depend accidentally on translated labels.

## Privacy and data minimization

Where personal/private data exists:
- verify collection/storage matches approved purpose;
- avoid unnecessary sensitive logging;
- verify exports/downloads are authorized;
- verify deletion/retention behavior if required;
- ensure test fixtures/package do not include real user data.

Do not claim regulatory compliance unless the project has an approved compliance target and the necessary legal/policy evidence.

## Compatibility

When explicitly supported:
- browser/device versions;
- API version/backward compatibility;
- DB/runtime versions;
- rolling deployment compatibility;
- mobile/responsive breakpoints.

Test the supported matrix proportionally to risk and tooling availability.
