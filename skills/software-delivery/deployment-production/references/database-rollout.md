# Database, Data, Queue, Cache, and Storage Rollout

## Table of contents

1. Scope
2. Data-system inventory
3. Migration classification
4. Expand-contract pattern
5. Migration execution
6. Destructive changes
7. Data backfills
8. Rollback versus roll-forward
9. Queue and worker compatibility
10. Scheduler safety
11. Cache compatibility
12. Object storage and files
13. Search/index/vector stores
14. Connection pools and readiness
15. Validation matrix
16. Failure conditions

## 1. Scope

Use this reference whenever a release changes durable state, schemas, data formats, background processing, cache semantics, object storage, search indexes, or other stateful dependencies.

The central rule is to preserve compatibility across the deployment window. A release is not safe merely because the final schema matches the new code.

## 2. Data-system inventory

For every stateful dependency, record:

- engine/service;
- version;
- endpoint ownership;
- persistence model;
- backup responsibility;
- encryption expectations;
- schema/data versioning method;
- connection/auth model;
- high availability/failover assumptions if any;
- migration path;
- failure behavior;
- production-like validation method.

Do not assume cache/queue/storage are stateless just because the application can reconnect to them.

## 3. Migration classification

Classify each schema/data change:

- additive: new nullable column/table/index compatible with old code;
- constraint change: nullability/foreign key/check/unique behavior changes;
- destructive: drop/rename/truncate/type narrowing;
- transformational: existing data rewritten/re-encoded;
- high-lock-risk: operation may block large tables;
- long-running backfill;
- online-compatible or requires maintenance window;
- reversible, conditionally reversible, or irreversible.

Record the classification in the release report for all material migrations.

## 4. Expand-contract pattern

For rolling/zero-downtime-compatible systems, prefer three logical steps:

### Expand

Add new schema structures in a form compatible with old and new application versions. Examples:

- add nullable column;
- add new table;
- add new index using online/concurrent mechanism when supported;
- introduce new field while old field remains readable.

### Migrate/use-both

Deploy code that can operate across old/new representation, dual-read/write only when correctness is carefully defined, and perform backfill if needed.

Avoid uncontrolled indefinite dual-write because divergence creates a new correctness problem. Define source of truth and reconciliation.

### Contract

Only after old code no longer depends on old schema/data representation and migration is verified, remove obsolete columns/tables/fields in a later release when feasible.

Do not combine expand and destructive contract in one rollout when old and new instances can overlap.

## 5. Migration execution

Define exactly:

- command/tool;
- working directory/image;
- credentials source;
- target database selection guard;
- migration lock/concurrency behavior;
- timeout;
- retry policy;
- transaction behavior;
- operator or CI job responsible;
- order relative to app deployment;
- expected output/status check;
- failure handling.

Avoid running migrations concurrently from every application replica unless the migration tool provides safe locking and the project intentionally relies on it.

Prefer a dedicated release/migration job for multi-replica systems.

Add a guard against accidentally running destructive migrations against the wrong environment when practical.

## 6. Destructive changes

Before a destructive migration:

1. Confirm necessity.
2. Identify affected rows/objects and data-loss impact.
3. Verify backup/snapshot prerequisites.
4. Verify restore procedure and expected time.
5. Confirm old application versions no longer need the structure.
6. Assess lock/downtime impact.
7. Require explicit production authorization if the operation is irreversible/high risk.
8. Prefer staged cleanup in a later release.

Never label a destructive SQL down-migration as safe merely because syntax exists.

## 7. Data backfills

For large/long-running backfills:

- separate from request startup;
- make resumable/checkpointed;
- make idempotent where feasible;
- process in bounded batches;
- bound transaction size;
- rate-limit to protect primary workload;
- track progress and errors;
- define retry/dead-letter handling;
- validate counts/checksums/sample correctness;
- define completion criteria;
- avoid holding schema/table locks unnecessarily.

If a backfill changes business-critical data, include domain-specific reconciliation.

## 8. Rollback versus roll-forward

Distinguish:

- application rollback;
- configuration rollback;
- schema rollback;
- data rollback.

Application rollback is safe only if the previous version remains compatible with the current schema/data.

If a migration destroys or transforms data irreversibly, prefer roll-forward or restore from a verified backup according to the incident plan. State this explicitly.

Never promise "one-click rollback" without checking schema/data compatibility.

## 9. Queue and worker compatibility

For messages/jobs crossing a deployment boundary:

- identify schema/version of payloads;
- determine whether old workers can consume new messages and vice versa;
- avoid changing meaning of existing fields incompatibly;
- add versioning when needed;
- define retry and dead-letter behavior;
- bound retry storms;
- ensure idempotency/deduplication where duplicates are possible;
- check visibility timeout/ack semantics;
- define poison-message handling;
- validate worker graceful shutdown.

During rolling deployment, producers and consumers may run different versions simultaneously. Design for that overlap or coordinate deployment order explicitly.

## 10. Scheduler safety

For cron/scheduled jobs:

- ensure only intended number of schedulers run;
- use distributed locking/leader election where multiple replicas would duplicate work;
- make jobs idempotent where practical;
- record timezone;
- bound execution duration;
- prevent overlapping runs if unsafe;
- emit success/failure/latency metrics;
- define retry behavior;
- consider missed runs during deploy/restart.

## 11. Cache compatibility

Treat cache as an optimization unless the system explicitly stores authoritative state there.

For releases:

- namespace/version cache keys when representation changes;
- avoid deserializing old incompatible payloads blindly;
- define TTL;
- handle cache miss correctly;
- avoid requiring a global flush unless justified;
- protect against cache stampede if rollout invalidates large keysets;
- validate behavior when cache is unavailable if the architecture expects degradation.

If sessions live in cache, treat it as durable/security-sensitive state and analyze logout/session invalidation behavior.

## 12. Object storage and files

Verify:

- bucket/container names are environment-scoped;
- credentials are least privilege;
- public/private ACL policy is explicit;
- server-side encryption policy if required;
- object key naming compatibility;
- MIME/content-type behavior;
- upload size limits;
- lifecycle/retention rules;
- versioning when recovery depends on it;
- signed URL expiry and scope;
- malware/content validation where relevant;
- local filesystem is not accidentally used for durable production uploads.

When changing object format/path, preserve compatibility or provide migration.

## 13. Search/index/vector stores

For secondary indexes:

- define rebuild path from source of truth;
- version index/schema names when incompatible;
- use alias/switch patterns where supported;
- validate indexing lag;
- validate rollback to previous application version;
- avoid treating a non-authoritative index as the only backup of data.

For vector stores, include embedding-model/version compatibility and reindex implications.

## 14. Connection pools and readiness

Verify production pool configuration:

- max pool size relative to replica count and database limits;
- connection timeout;
- idle timeout;
- retry/backoff;
- TLS settings;
- transaction timeout where appropriate;
- graceful connection close on shutdown.

Readiness should fail when the service cannot safely serve its critical path, but liveness should not necessarily fail for every transient database outage.

## 15. Validation matrix

At minimum validate applicable rows:

| Area | Before deploy | During rollout | After deploy |
|---|---|---|---|
| schema version | expected current | migration progress/lock | expected target |
| old/new app compatibility | analyze | mixed-version check | target only |
| backup | verify/snapshot | protect | retain per policy |
| backfill | dry/sample | progress/errors | reconcile |
| queue | payload compatibility | backlog/retry | error/DLQ check |
| scheduler | ownership | duplicate-run guard | next-run health |
| cache | key compatibility | miss/load behavior | error rate |
| object storage | access policy | upload/read | lifecycle/permissions |

## 16. Failure conditions

Fail `G05_DATABASE_AND_DATA` when applicable and unresolved:

- migration cannot run successfully;
- old/new versions are incompatible during required rollout overlap;
- destructive change lacks recovery prerequisite;
- migration can target the wrong production database without reasonable guard in a high-risk workflow;
- job/queue change can silently corrupt or duplicate critical work;
- scheduler would duplicate unsafe jobs across replicas;
- durable uploads/data remain on ephemeral local storage unexpectedly;
- rollback plan contradicts actual schema/data compatibility.
