# Backend, API, Data, Migration, Concurrency, and Idempotency Testing

## Purpose

Provide detailed rules for server-side boundaries where silent correctness failures are common.

## Table of contents

1. Service/application logic
2. Repository and SQL integration
3. Transactions
4. API contracts
5. Pagination/filtering/sorting
6. Idempotency
7. Concurrency
8. Caches and queues
9. Migration testing
10. Backfill/data transformation
11. File/object storage
12. Failure injection

## 1. Service/application logic

Test domain/application behavior around:
- allowed/forbidden state transitions;
- invariant enforcement;
- calculations and rounding;
- duplicate detection;
- retry policies;
- domain events;
- command validation;
- error mapping.

Keep pure logic at unit level. Move to integration when persistence, transaction, or framework behavior is material.

## 2. Repository and SQL integration

Use a real compatible database engine for integration tests when production behavior depends on engine semantics.

Test as applicable:
- NOT NULL;
- UNIQUE;
- foreign keys;
- CHECK constraints;
- enum/domain constraints;
- indexes when correctness depends on uniqueness/query semantics;
- generated/default values;
- cascade/restrict behavior;
- serialization of dates/decimals/JSON;
- soft-delete scoping;
- tenant scoping;
- optimistic lock/version fields.

Do not assume SQLite proves MySQL/PostgreSQL-specific behavior unless the application deliberately supports SQLite semantics.

## 3. Transactions

For critical multi-step writes, test:
- full success commits all intended changes;
- failure midway rolls back according to contract;
- external side effects are not incorrectly committed before DB state;
- outbox/event publication semantics if used;
- retry after rollback is safe;
- nested transaction/savepoint behavior if relied upon.

Inspect final persisted state, not only thrown errors.

## 4. API contracts

For each P0/P1 endpoint family, cover as applicable:
- valid request;
- unauthenticated request;
- authenticated-but-forbidden request;
- wrong owner/tenant;
- missing required field;
- wrong type;
- malformed JSON/form payload;
- boundary-length values;
- duplicate request;
- stale version/ETag when applicable;
- resource missing;
- invalid state transition;
- expected response schema;
- stable error code/message identifier;
- content type;
- no unintended sensitive fields.

For write endpoints, assert persisted side effects and forbidden side-effect absence.

## 5. Pagination, filtering, sorting, and search

Test:
- first page;
- last partial page;
- empty result;
- page/limit boundaries;
- maximum allowed limit;
- invalid cursor/page;
- stable ordering/tie behavior;
- filter combinations;
- tenant/ownership filters cannot be bypassed;
- search escaping/wildcards;
- deterministic cursor continuation if cursor-based pagination is used.

Avoid test datasets too small to reveal pagination defects.

## 6. Idempotency

For operations that may be retried or submitted twice, define the intended key/identity and test:
- same request + same idempotency key;
- same key + different payload;
- concurrent same-key requests;
- retry after timeout/ambiguous response;
- key expiry if specified;
- persistence of idempotent result;
- side effects occur at most once.

Money movement, order creation, callbacks, and job processing frequently deserve P0/P1 idempotency tests.

## 7. Concurrency

Do not claim concurrency safety from serial tests.

Where races are plausible, test concurrent actors for:
- double spend;
- duplicate reservation;
- inventory/limit oversubscription;
- double approval;
- lost update;
- stale version conflict;
- unique constraint race;
- job duplicate processing;
- lock timeout/retry.

Use barriers/latches or coordinated concurrent requests rather than arbitrary sleeps.

Assert the invariant after all workers finish.

If concurrency tests are timing-sensitive, repeat them enough to establish reliability and keep deterministic coordination where possible.

## 8. Caches and queues

### Cache

Test:
- miss → load → hit;
- invalidation after write;
- stale value behavior where specified;
- tenant/user key isolation;
- fallback when cache unavailable;
- no authorization decision incorrectly trusted from stale cross-user cache.

### Queue/background job

Test:
- message schema;
- handler success;
- retryable failure;
- permanent failure/dead-letter behavior when implemented;
- duplicate delivery/idempotency;
- ordering assumptions if any;
- transaction/outbox coupling;
- poison message handling.

## 9. Migration testing

For every migration in Stage 09 scope, determine whether it is:
- additive schema;
- destructive schema;
- data migration/backfill;
- index/constraint change;
- table split/merge;
- type/encoding change.

At minimum where applicable, test:

### Fresh install path

1. create an empty disposable database;
2. run all migrations from zero;
3. verify migration success;
4. verify critical schema constraints;
5. run representative application integration tests.

### Supported upgrade path

1. construct or restore a representative pre-migration schema/data state;
2. insert boundary/legacy data cases;
3. run the migration;
4. verify data preservation/transformation;
5. verify constraints/indexes/defaults;
6. run relevant application tests.

### Rollback path

Test rollback only when rollback is an explicitly supported project capability. Do not invent rollback guarantees the project does not promise.

If migration is intentionally irreversible, verify the forward migration is safe and document rollback strategy from prior stages if one exists.

## 10. Backfill and data transformation

Test:
- empty dataset;
- normal dataset;
- null/legacy values;
- maximum/large values;
- duplicate/conflicting rows;
- restartability/idempotency when backfill can rerun;
- partial failure recovery;
- batch boundaries;
- expected row counts/checksums when practical.

Never run destructive backfill tests on production data.

## 11. File/object storage

Test:
- allowed type/size;
- forbidden type/size;
- metadata persistence;
- ownership/access control;
- missing object behavior;
- partial upload failure;
- cleanup after DB failure;
- signed URL scope/expiry where applicable;
- path/key collision;
- filename/path traversal normalization at the appropriate security layer.

Use disposable local object storage/emulator or adapter fake according to project architecture.

## 12. Failure injection

For critical workflows, deliberately inject realistic failures:
- database exception;
- deadlock/lock timeout when practical;
- queue failure;
- external timeout;
- cache unavailable;
- storage failure;
- duplicate callback;
- stale version.

The goal is to prove safety invariants, not merely increase branch coverage.
