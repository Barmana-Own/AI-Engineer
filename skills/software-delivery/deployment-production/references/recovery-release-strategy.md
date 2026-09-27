# Release Strategy, Backup, Restore, Rollback, and Incident Recovery

## Table of contents

1. Purpose
2. Deployment strategy selection
3. Rolling deployments
4. Blue-green deployments
5. Canary deployments
6. Recreate/maintenance deployments
7. Pre-deploy change controls
8. Backup model
9. Restore verification
10. RPO and RTO
11. Rollback matrix
12. Roll-forward
13. Failed migration recovery
14. Configuration and secret rollback
15. Incident stabilization
16. Post-deploy watch
17. Failure conditions

## 1. Purpose

Use this reference to make release failure survivable. The goal is not to promise zero downtime; the goal is to select a rollout model consistent with architecture, verify recovery paths, and define when to stop or reverse a release.

## 2. Deployment strategy selection

Choose based on actual system properties:

- number of replicas;
- statefulness;
- database compatibility;
- session behavior;
- traffic routing capability;
- target platform features;
- release frequency;
- acceptable downtime;
- operational maturity;
- rollback cost;
- migration risk.

Record the chosen strategy and why alternatives are unnecessary or unsafe.

## 3. Rolling deployments

Use when old/new versions can safely coexist and the platform supports incremental replacement.

Require:

- mixed-version API/schema/message compatibility;
- readiness before traffic;
- graceful shutdown before termination;
- enough capacity during replacement;
- session handling compatible with instance replacement;
- migration ordering compatible with overlap.

Do not use rolling deployment for an incompatible destructive schema change without a staged expand-contract plan.

## 4. Blue-green deployments

Use when the target supports two full environments/revisions and switching traffic is useful.

Require:

- environment parity;
- clear source/artifact identity for blue and green;
- shared state compatibility;
- traffic switch mechanism;
- health/smoke on inactive environment;
- rollback switch conditions;
- handling of irreversible writes that occur after traffic switches.

Blue-green application rollback does not magically undo schema/data changes.

## 5. Canary deployments

Use when traffic segmentation and meaningful telemetry exist.

Define:

- canary population/percentage;
- duration or sample threshold;
- success/error/latency criteria;
- business correctness signals if relevant;
- automatic/manual promotion rule;
- rollback threshold;
- telemetry segmentation by release.

A canary without release-specific metrics cannot safely prove the new version is better/healthy.

## 6. Recreate/maintenance deployments

Use when the system is single-instance, stateful/incompatible, or downtime is acceptable and safer than mixed versions.

Require:

- maintenance communication if relevant;
- backup/migration prerequisites;
- explicit downtime expectation;
- startup/smoke verification before reopening traffic;
- rollback/restore path.

Do not pretend recreate is zero downtime.

## 7. Pre-deploy change controls

Before any real production mutation verify:

- explicit authorization;
- target/environment identity;
- source commit/ref;
- artifact/image digest;
- current service baseline;
- backup/snapshot prerequisite;
- migration plan;
- deploy credential scope;
- change window if required;
- rollback/roll-forward trigger;
- operator ownership;
- no P0/P1 blocker.

Record authorization as a fact, not as a secret. Never copy approval tokens or credentials into evidence.

## 8. Backup model

Inventory all durable state and assign a backup/recovery mechanism. This may include:

- relational databases;
- NoSQL databases;
- object storage;
- user-uploaded files;
- search indexes when not reconstructable;
- persistent queues when business semantics require it;
- configuration/secrets where recoverable configuration is not already IaC/managed;
- encryption keys/KMS dependencies where loss would make backups useless.

For each backup define:

- mechanism;
- schedule/trigger;
- retention;
- storage location/isolation;
- encryption;
- access control;
- immutability/versioning when needed;
- monitoring for failed backups;
- restore prerequisites;
- deletion/lifecycle policy.

Keep recovery copies independent enough that loss/compromise of the primary system does not automatically destroy every backup.

## 9. Restore verification

Prefer an actual non-production restore drill:

1. choose a known backup/snapshot;
2. restore into isolated non-production target;
3. verify schema/database opens;
4. run integrity checks;
5. validate representative application queries/workflows;
6. record restore duration;
7. record data point/time recovered;
8. clean up safely.

If a restore drill cannot be run, document exactly why and what evidence exists instead. Do not call an untested backup "verified recovery."

## 10. RPO and RTO

RPO: maximum acceptable data loss window.

RTO: maximum acceptable service recovery time.

Do not invent contractual values. Use existing requirements. If absent, record proposed operational targets as assumptions requiring owner acceptance.

Check whether the actual backup frequency and restore procedure could meet the stated/proposed targets. A daily backup cannot satisfy a five-minute RPO.

## 11. Rollback matrix

Build a release-specific matrix:

| Layer | Rollback mechanism | Safe after current change? | Evidence/prerequisite |
|---|---|---|---|
| app artifact | previous immutable artifact | yes/no | old/new compatibility |
| config | previous config version | yes/no | config version history |
| schema | down migration/none | yes/no | migration analysis |
| data | restore/reconcile/none | yes/no | backup + data impact |
| infrastructure | IaC/revision rollback | yes/no | state/plan |
| client/static assets | prior artifact/CDN version | yes/no | cache behavior |

Do not write "rollback: redeploy previous version" without filling in schema/data compatibility.

## 12. Roll-forward

Prefer roll-forward when:

- new schema is backward compatible but previous app is not desirable;
- data transformation is irreversible;
- rollback would lose valid new writes;
- fix can be safely deployed faster than restore;
- target platform encourages immutable forward revisions.

Define the minimal fix path and how to keep the service safe while preparing it.

## 13. Failed migration recovery

Classify the failure:

- migration never started;
- transaction rolled back cleanly;
- partially applied DDL/data;
- application already started against incomplete schema;
- long-running lock/timeout;
- backfill partially completed.

Then:

1. stop additional migration actors;
2. protect data and preserve logs/status;
3. determine exact applied state;
4. decide continue/repair/restore based on engine and change semantics;
5. keep incompatible app versions out of traffic;
6. validate integrity before resuming rollout.

Never blindly rerun a non-idempotent migration after partial application.

## 14. Configuration and secret rollback

Version configuration where the platform supports it. For a bad config release:

- identify the exact changed keys;
- restore previous safe values;
- restart/reload only the components required;
- verify health;
- preserve audit evidence.

For compromised credentials, rollback to an old compromised credential is not recovery. Rotate/revoke and redeploy safe credentials.

## 15. Incident stabilization

During an active failed release prioritize:

1. stop harmful mutation/traffic if needed;
2. preserve data and evidence;
3. restore a known safe service state;
4. communicate ownership/status according to project process;
5. diagnose root cause after stabilization.

Do not keep applying speculative changes directly in production without recording source/artifact identity.

## 16. Post-deploy watch

Define an early-release observation window or criteria appropriate to the system. Check:

- availability/error rate;
- latency;
- resource saturation;
- restarts/crashes;
- database errors/locks;
- queue age/failures;
- external dependency errors;
- critical business transaction success;
- support/error-reporting spike.

For canary/blue-green, compare signals by release cohort/environment when possible.

## 17. Failure conditions

Fail recovery/release gates when unresolved:

- high-risk data change has no viable recovery control;
- rollback claims contradict irreversible migration/data behavior;
- backups exist but no one knows how to restore them and project criticality requires tested recovery;
- rollout strategy requires mixed-version compatibility that does not exist;
- canary has no release-specific success/failure measurement;
- real deployment would proceed without required authorization or target identity;
- failed release has no safe stop/rollback/roll-forward decision.
