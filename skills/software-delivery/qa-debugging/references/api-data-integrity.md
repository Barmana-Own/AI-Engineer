# API and Data-Integrity Verification

## Table of contents

1. Scope
2. Contract verification
3. Authentication and authorization
4. Validation and error semantics
5. Mutation integrity
6. Transactions and atomicity
7. Idempotency and replay
8. Concurrency
9. Query behavior
10. Database invariants
11. Queue, cache, and job consistency
12. Webhooks and integrations
13. Migration compatibility
14. Evidence and exit criteria

## 1. Scope

Use this reference whenever Stage 10 includes APIs, persistence, queues, caches, jobs, webhooks, or other stateful server behavior. Verify both API-visible behavior and resulting domain state.

## 2. Contract verification

For release-critical endpoints verify:

- method and route;
- required headers/content type;
- authentication requirement;
- request schema;
- status codes;
- response schema;
- error shape;
- pagination/filter/sort semantics;
- versioning assumptions;
- documented side effects.

Do not assume a `200` means the domain operation succeeded correctly. Verify the resulting state.

## 3. Authentication and authorization

For protected endpoints:

- no credential -> denied;
- invalid/expired credential -> denied;
- allowed role -> succeeds;
- forbidden role -> denied;
- owner -> succeeds when ownership grants access;
- non-owner -> denied;
- direct object-ID substitution -> denied where applicable;
- hidden UI capability -> still denied server-side.

Use benign test identities and objects.

## 4. Validation and error semantics

Verify server-side behavior for:

- missing required field;
- wrong type;
- invalid enum;
- malformed identifier;
- too-long value;
- invalid foreign reference;
- cross-field inconsistency;
- unexpected extra/mass-assignment field where relevant;
- duplicate uniqueness constraints;
- invalid file metadata.

Error responses should be stable enough for clients to handle and must not expose secrets, stack traces, internal SQL, or sensitive configuration.

## 5. Mutation integrity

For create/update/delete/approve/pay/submit-like endpoints verify:

- one intended mutation causes one intended state change;
- duplicate/replayed requests do not create unintended duplicates;
- failures do not report false success;
- server derives privileged fields rather than trusting client-controlled values;
- immutable fields remain immutable;
- status transitions obey domain rules;
- audit fields/timestamps are coherent where required;
- related records remain consistent.

## 6. Transactions and atomicity

For multi-record or multi-step mutations inspect whether partial failure can leave inconsistent state.

Test or reason from executed evidence around:

- parent created but child missing;
- balance updated but ledger missing;
- status changed but event/job not enqueued;
- file stored but DB record failed;
- DB row committed but external side effect failed.

Expected behavior may be atomic rollback, compensation, retryable outbox/event flow, or another documented pattern. The key requirement is deterministic consistency, not a specific architecture.

## 7. Idempotency and replay

For operations vulnerable to retries:

- send same request twice;
- retry after ambiguous timeout;
- reuse idempotency key where supported;
- replay webhook/event where safe;
- process queue message twice if test harness supports it.

Verify no duplicate financial, inventory, notification, or workflow side effect occurs unless explicitly intended.

## 8. Concurrency

For high-value shared resources test where practical:

- simultaneous updates;
- approve/approve race;
- approve/cancel race;
- update/delete race;
- duplicate creation under uniqueness constraint;
- stale version update.

Verify conflict handling, locking/versioning, uniqueness, or domain guard behavior. Record if concurrency could not be executed.

## 9. Query behavior

Verify important read endpoints for:

- authorization filtering;
- empty results;
- stable ordering;
- pagination edges;
- filter combinations;
- invalid filter values;
- large page-size limits;
- archived/deleted visibility;
- tenant/organization isolation;
- count metadata consistency.

## 10. Database invariants

When safe DB inspection is available, verify important invariants after mutations:

- foreign keys/reference consistency;
- uniqueness;
- non-null domain requirements;
- valid enum/status values;
- parent/child counts;
- aggregate consistency;
- audit timestamps;
- soft-delete semantics;
- no orphaned file/job/event references;
- no impossible transition state.

Do not weaken constraints to make tests pass without proving the constraint conflicts with approved requirements.

## 11. Queue, cache, and job consistency

### Queues/jobs

Check:

- message produced once as expected;
- retry policy does not duplicate irreversible effects;
- poison/failing jobs are observable;
- failed jobs do not silently mark workflow complete;
- correlation identifiers exist when project conventions require them.

### Cache

Check:

- mutation invalidates/updates relevant cache;
- role/permission changes are not hidden by stale cache;
- stale cache cannot expose unauthorized data;
- UI/API reflects canonical state within documented consistency rules.

## 12. Webhooks and integrations

Verify:

- request signing/verification when required;
- event type validation;
- duplicate event handling;
- out-of-order event handling where provider can deliver that way;
- timeout/error handling;
- retry safety;
- unknown event behavior;
- secret values are not logged.

If no live sandbox is available, test the local contract and failure handling using controlled fixtures and mark live behavior unverified.

## 13. Migration compatibility

Stage 10 is not migration design, but release QA should confirm:

- current release starts against expected migrated schema;
- migrations apply in the test environment when safe;
- code does not reference missing/new columns incorrectly;
- seeds/fixtures remain compatible;
- rollback assumptions are not falsely claimed if not tested.

Do not run destructive migration experiments on production data.

## 14. Evidence and exit criteria

Record for critical mutations:

- request/action;
- response;
- resulting database/domain state;
- downstream event/job/notification state where relevant;
- failure behavior;
- authorization result.

Before PASS, no known P0/P1 data-integrity, cross-tenant, ownership, or critical mutation defect may remain open.
