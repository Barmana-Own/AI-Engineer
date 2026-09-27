# Transactions, Concurrency, and Idempotency

## Transaction boundary

A transaction should protect a business invariant, not merely wrap every repository call. Keep transactions short and do not hold database locks across slow network calls unless architecture explicitly requires a transactional outbox/saga pattern.

For each transactional use case document:
- records/tables affected;
- invariant protected;
- isolation assumption;
- lock/version behavior;
- failure/rollback expectation;
- retry semantics.

## Lost updates

For user-editable mutable rows, decide whether last-write-wins is acceptable. If not, use optimistic versioning, conditional updates, or explicit locking.

Test that stale writers cannot silently overwrite newer data when the invariant requires conflict detection.

## Uniqueness races

Application pre-checks are insufficient under concurrency. Back them with a unique constraint or equivalent durable serialization mechanism and map the violation to a stable domain/application error.

## Capacity/quota/balance races

When two concurrent operations can consume the same resource:
- use atomic conditional updates, row locks, serializable logic, or another database-supported strategy;
- test concurrent execution;
- avoid read-then-write without protection.

## Idempotency

For retried commands/payments/webhooks/API writes, define:
- idempotency key scope;
- uniqueness storage;
- request fingerprint if needed;
- stored result/replay behavior;
- expiry/retention;
- behavior when the same key is reused with different payload.

Database uniqueness should normally backstop idempotency-key creation.

## Deadlocks and retries

Use consistent lock/update ordering where possible. When the engine can legitimately deadlock under concurrent transactions, retry only operations that are safe to retry and bound retry attempts.

## Outbox/inbox

If persistence and message/event publication must be atomic, consider a transactional outbox. If event consumption can replay, define inbox/deduplication semantics. Do not add these patterns unless Stage 04/integration requirements justify them.
