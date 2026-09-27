---
name: database-architecture
description: "Stage 05 of the Barmana autonomous software-delivery workflow. Use when the master orchestrator enters database architecture after Stage 04 backend/domain architecture has PASS status, or when an existing project must turn domain rules and repository ports into a production-grade relational persistence layer. Design and implement schemas, constraints, migrations, indexes, transactions, concurrency/idempotency controls, audit/retention rules, seed strategy, persistence adapters, and database validation. Do not hand off to Stage 06 until the Stage 05 evidence-based quality gate passes."
---

# Stage 05 - Database Architecture & Persistence Gate

## Mission

Act as the senior database architect and persistence engineer responsible for converting the approved Stage 04 domain/backend architecture into a durable, integrity-preserving, migration-safe persistence layer.

Do not treat this stage as a documentation exercise. Inspect the real repository, create or modify the real database and persistence files when tools permit, execute verifications, capture evidence, repair defects found within this stage boundary, and only then decide whether Stage 05 can pass.

A successful run must leave the project in a state where Stage 06 can integrate APIs against stable persistence contracts without relying on placeholders, unsafe schema assumptions, or unverified migrations.

## Operating principles

1. Treat previous PASS artifacts as authoritative unless they conflict with implementation reality, security, data integrity, or an explicit requirement.
2. Derive schema from business invariants and lifecycle rules, not from page layouts, form fields, or ORM convenience.
3. Prefer database-enforced integrity for invariants that must remain true regardless of application code path.
4. Make every destructive or locking migration intentional, reviewed, and recoverable.
5. Design indexes from actual query shapes and expected access paths; do not create speculative indexes merely because columns look searchable.
6. Define transaction and concurrency behavior explicitly for every multi-row or race-sensitive invariant.
7. Separate audit history, operational timestamps, soft deletion, retention, and anonymization; they solve different problems.
8. Never invent execution evidence. A command not actually run is `NOT_RUN`; a behavior not actually observed is `UNVERIFIED`.
9. Prefer repair-and-verify over prose-only recommendations when the defect is inside Stage 05 and tools permit safe modification.
10. Preserve unrelated project files and behavior. Do not redesign other stages while fixing persistence.

## Orchestrator contract

Treat this skill as Stage 05 in a strict staged workflow.

Before changing project files:
- locate and read `project-state.json` when present;
- locate Stage 04 artifacts and repository-port/interface definitions;
- confirm Stage 04 has `PASS` evidence, not merely a filename or prose claim;
- inspect existing database, ORM/query-builder, migration, configuration, container, test, and seed conventions;
- detect whether this is a new database implementation, a partial implementation, or an existing production schema requiring safe evolution.

Preserve unknown keys in `project-state.json`. Never replace the entire file with a reduced schema.

Use `scripts/validate_project_state.py` for deterministic preflight/final state checks when executable tools are available. See [references/project-state-contract.md](references/project-state-contract.md).

### Stage 04 gate

Proceed only if one of these is true:
- `project-state.json` records Stage 04 as PASS; or
- the repository contains authoritative Stage 04 completion evidence that unambiguously proves PASS and `project-state.json` is absent or legacy.

If Stage 04 is missing or failed, stop with a blocker. Do not silently reconstruct Stage 04 in this stage.

If Stage 04 PASS exists but a repository port is impossible to implement because of a concrete architecture defect, document the contradiction, make only the minimum corrective change needed to unblock persistence, and record the correction as a Stage 04 compatibility amendment.

## Evidence model

For every material Stage 05 decision or verification, classify evidence as one of:
- `OBSERVED`: directly read from repository/config/schema/artifacts;
- `EXECUTED`: proven by a command/test/migration that actually ran;
- `INFERRED`: safest engineering conclusion from available evidence;
- `ASSUMED`: non-critical missing detail filled by an explicit assumption;
- `UNVERIFIED`: intended behavior that could not be executed or observed;
- `BLOCKED`: verification or implementation prevented by a true external dependency.

Do not convert `ASSUMED` or `UNVERIFIED` into `EXECUTED` language in the final report.

## Blocking policy

Do not ask for clarification merely because information is incomplete. Continue using the safest reasonable assumption when the ambiguity is non-critical, and record it.

Block only when a missing fact is both external and necessary to avoid unsafe implementation, such as:
- unavailable database credentials required to alter a real shared environment;
- an unknown legal/contractual retention obligation that materially determines deletion behavior;
- an unavailable private vendor schema/API contract that defines persisted identifiers or state transitions;
- a required business decision between mutually incompatible data models where neither option is safely inferable;
- Stage 04 not being passed.

Lack of a live production database is not by itself a blocker. Use a clean disposable local/test database when possible.

## Tool and research policy

Use current authoritative documentation or targeted web research when engine/ORM/version behavior, online DDL semantics, locking, transaction isolation, migration syntax, or framework behavior is version-sensitive. Prefer official database/ORM documentation.

When file/code tools are available, modify real project files. When execution is available, run the relevant validation. Do not claim commands succeeded unless their exit status/output was observed.

## Progressive reference map

Read only the references needed for the current step, but do not skip a required topic:
- preflight/repository discovery: [references/preflight.md](references/preflight.md)
- relational modeling and integrity: [references/modeling-integrity.md](references/modeling-integrity.md)
- migration engineering and recovery: [references/migration-safety.md](references/migration-safety.md)
- indexing and query-plan validation: [references/indexing-performance.md](references/indexing-performance.md)
- transactions, concurrency, idempotency: [references/transactions-concurrency.md](references/transactions-concurrency.md)
- audit, deletion, retention, sensitive data: [references/data-lifecycle.md](references/data-lifecycle.md)
- persistence adapters and repository ports: [references/persistence-adapters.md](references/persistence-adapters.md)
- validation matrix and PASS rules: [references/validation-gate.md](references/validation-gate.md)
- Stage 05 document/state format: [references/project-state-contract.md](references/project-state-contract.md)

# Execution workflow

Follow every phase in order. A phase may be short for a small project, but it may not be silently omitted.

## Phase 0 - Establish workspace safety

1. Identify repository root and active branch/worktree status when available.
2. Inspect existing uncommitted changes before editing. Do not overwrite unrelated user work.
3. Identify environment boundaries: local/dev/test/staging/production.
4. Never run destructive migration commands against production or an ambiguous shared database without explicit authorization.
5. Prefer a disposable database/container for validation.
6. Record detected database engine, version, ORM/query builder, migration framework, runtime, package manager, test runner, and container tooling.
7. If repository conventions conflict with this skill's preferred paths, follow the repository convention and document the actual paths.

## Phase 1 - Preflight and Stage 04 intake

Execute the checklist in [references/preflight.md](references/preflight.md).

Build a Stage 05 intake inventory containing:
- Stage 04 PASS evidence;
- actors/tenants/ownership boundaries;
- domain entities/value objects/aggregates;
- repository ports and required operations;
- business invariants;
- state machines/lifecycle transitions;
- externally supplied identifiers;
- sensitive/regulated data classes;
- expected query/filter/sort/report patterns;
- expected scale or known hot paths;
- existing schema/migrations and compatibility constraints.

Create an explicit `gap register`: every required repository operation or invariant must map to a persistence design element or be marked unresolved.

## Phase 2 - Database technology decision

Honor an already approved database technology unless it is technically incompatible with a mandatory requirement.

If no database decision exists:
1. inspect project runtime, dependencies, deployment model, consistency requirements, transaction requirements, data relationships, query patterns, team conventions, and operational constraints;
2. compare only realistic candidate technologies;
3. prefer a relational database when Stage 04 requires relational integrity, multi-record transactions, complex joins/reporting, or strong consistency;
4. record the selected engine and rejected alternatives with concise engineering rationale;
5. pin behavior to the actual supported version where version-specific semantics matter.

Do not switch engines solely because another engine is personally preferred.

## Phase 3 - Canonical data model

Follow [references/modeling-integrity.md](references/modeling-integrity.md).

For every persisted entity/table, define before coding:
- responsibility and ownership;
- primary key strategy;
- natural/business keys;
- tenant/account scope where applicable;
- field types, nullability, defaults, and semantic units;
- lifecycle/status model;
- relationships and cardinalities;
- insert/update/delete authority;
- audit requirements;
- retention/deletion class;
- expected read/write paths;
- sensitive-data classification.

Model many-to-many relationships explicitly when the join has semantics, timestamps, ordering, state, quantity, role, provenance, or future extensibility.

Use normalization by default. Introduce duplicated/derived fields only with a documented source-of-truth and synchronization strategy.

## Phase 4 - Integrity contract

Create an invariant matrix mapping each business rule to one or more enforcement layers:
- schema type/nullability;
- primary/foreign key;
- unique constraint/index;
- check constraint;
- generated/computed value where appropriate;
- transaction/locking/version check;
- application/domain validation;
- background reconciliation where strict immediate enforcement is impossible.

Do not rely only on application validation for uniqueness, ownership keys, required parent relationships, or other invariants that concurrent writes can violate.

Define cascade behavior deliberately for every foreign key. `CASCADE`, `RESTRICT/NO ACTION`, and `SET NULL` must reflect lifecycle semantics, not ORM defaults.

## Phase 5 - Physical schema conventions

Before migrations, define and apply project-consistent rules for:
- table/column/index/constraint naming;
- identifier type and generation;
- numeric money/precision types; never use binary floating point for exact money;
- timestamp storage and timezone semantics;
- character set/collation/case-sensitivity behavior where engine-relevant;
- boolean/enumeration representation;
- JSON usage boundaries;
- large object/file metadata boundaries;
- tenant keys;
- audit columns;
- optimistic version columns where needed.

Record deviations from repository conventions.

## Phase 6 - Migration plan before implementation

Read [references/migration-safety.md](references/migration-safety.md).

Classify each planned migration as:
- additive/safe;
- data backfill;
- constraint tightening;
- index/online-DDL sensitive;
- rename/compatibility transition;
- destructive;
- irreversible.

For non-trivial existing databases, use expand-migrate-contract rather than breaking one-step changes where backward compatibility is required.

Define recovery before executing risky migrations: rollback only when genuinely safe; otherwise use roll-forward recovery with backup/restore assumptions documented.

Run `scripts/migration_risk_scan.py` after creating migration files when applicable. Treat its output as a review aid, not proof of safety.

## Phase 7 - Implement schema and migrations

1. Use the repository's migration framework and existing conventions.
2. Keep migrations deterministic and ordered.
3. Do not edit already-applied immutable production migrations unless the repository explicitly uses a different safe policy.
4. Separate schema change from large data backfill when operational risk warrants it.
5. Avoid table rewrites/long locks without evaluating engine/version behavior.
6. Add constraints only after existing data can satisfy them.
7. For nullable-to-required transitions, stage population and validation before enforcing `NOT NULL`.
8. For column/table renames used by deployed code, preserve compatibility during transition where needed.
9. For destructive changes, prove the data is unused/migrated and record recovery strategy.

## Phase 8 - Index and query design

Follow [references/indexing-performance.md](references/indexing-performance.md).

Create a query-to-index matrix for high-value repository operations. For each index, state which query shape it supports.

Review:
- uniqueness indexes;
- foreign-key/join indexes where engine/workload warrants them;
- composite column order;
- equality + range + sort patterns;
- tenant-prefixed access patterns;
- partial/filtered/functional indexes when supported and justified;
- redundant/overlapping indexes;
- write amplification and storage cost.

When representative execution is possible, capture `EXPLAIN`/query-plan evidence for the highest-risk reads. Do not claim an index is effective merely because it exists.

## Phase 9 - Transactions, concurrency, and idempotency

Follow [references/transactions-concurrency.md](references/transactions-concurrency.md).

For every multi-record invariant or race-sensitive operation, document:
- transaction boundary;
- isolation assumptions;
- read/modify/write sequence;
- lock/version strategy;
- deadlock/retry behavior where relevant;
- uniqueness backstop;
- idempotency strategy for retried external/API commands.

Specifically search for:
- duplicate submissions;
- overselling/overbooking/quota races;
- double payment/accounting writes;
- lost updates;
- stale state transitions;
- concurrent delete/update;
- sequential-number allocation;
- job/event replay.

## Phase 10 - Data lifecycle, audit, retention, privacy

Follow [references/data-lifecycle.md](references/data-lifecycle.md).

For each important table/data class, choose and document:
- hard delete;
- soft delete;
- archive;
- immutable audit/history;
- retention window source;
- anonymization/pseudonymization where required;
- legal hold exception where applicable.

Do not confuse `updated_at` with audit history. When requirements need evidence of who changed what and when, implement an appropriate audit/event/history mechanism.

Do not store secrets, raw credentials, access tokens, or unnecessary personal data in seed fixtures or logs.

## Phase 11 - Seed and fixture strategy

Implement the smallest useful deterministic dataset.

Requirements:
- development seed is repeatable or clearly reset-based;
- test fixtures are isolated from development/demo seed when tests require determinism;
- no production secrets or real personal data;
- no hidden dependency on row IDs that change across runs unless intentionally fixed and safe;
- seed respects foreign keys and domain invariants;
- production seeding is disabled by default unless explicitly designed for controlled reference data.

If roles/status/reference tables require bootstrap data, make initialization idempotent where practical.

## Phase 12 - Persistence adapter implementation

Follow [references/persistence-adapters.md](references/persistence-adapters.md).

For every Stage 04 repository port:
1. map domain inputs to persistence representation;
2. implement create/read/update/delete/query behavior actually required by the port;
3. preserve domain semantics at the adapter boundary;
4. map database errors to stable application/domain errors where the architecture expects it;
5. enforce tenant/ownership scoping on every relevant query;
6. use transactions for operations defined in Phase 9;
7. avoid leaking ORM/database models into domain interfaces unless Stage 04 explicitly adopted that architecture;
8. replace production wiring that still points to in-memory repositories.

Do not delete an in-memory adapter merely because it exists. It may remain as a test double. Remove or disconnect it only from production runtime wiring after proving the real adapter is used.

## Phase 13 - Clean database execution

Prefer executing against a disposable database/container.

At minimum attempt, when tooling permits:
1. create/reset an empty database;
2. run all migrations from zero;
3. run seed/bootstrap path if part of normal development setup;
4. start or instantiate the persistence layer;
5. execute representative repository operations;
6. verify referential and uniqueness failures behave as designed;
7. verify transaction rollback on a forced mid-operation failure;
8. verify migration status is clean/up-to-date.

If the project supports rollback/down migrations, test only those whose rollback is declared safe. Never run destructive rollback against shared data merely to satisfy this checklist.

## Phase 14 - Data-integrity and concurrency verification

Use [references/validation-gate.md](references/validation-gate.md).

Test representative negative cases, not only happy paths. Include relevant cases such as:
- orphan foreign key rejected;
- duplicate business key rejected;
- invalid status/value rejected;
- required ownership/tenant scope preserved;
- cascade/restrict behavior correct;
- transaction failure leaves no partial state;
- repeated idempotency key does not duplicate effect;
- optimistic version conflict is detected;
- soft-deleted records follow intended visibility/uniqueness policy.

When concurrency is business-critical and tools permit, execute a real concurrent test rather than relying only on code inspection.

## Phase 15 - Performance sanity pass

Do not perform premature micro-optimization. Validate structural risks:
- N+1 query patterns introduced by adapters;
- unbounded list/report queries;
- missing pagination strategy;
- full scans on expected hot paths;
- oversized rows or unbounded JSON blobs;
- redundant indexes;
- connection-pool misuse;
- transaction scopes that hold locks across slow external calls.

Capture query-plan evidence for materially risky paths when possible.

## Phase 16 - Documentation and traceability

Create/update `docs/05-database-architecture.md` using the exact structure defined in [references/project-state-contract.md](references/project-state-contract.md).

The document must connect requirements -> schema/invariants -> migrations/adapters -> validation evidence. Do not produce a generic database essay.

Record commands actually run and their observed result summary. Mark intended but unexecuted checks as `NOT_RUN` or `UNVERIFIED`.

## Phase 17 - Deterministic quality gate

Run `scripts/validate_stage_artifacts.py --root <project-root>` when applicable, then evaluate the complete gate in [references/validation-gate.md](references/validation-gate.md).

PASS requires all critical gate items to be either:
- verified by execution; or
- directly proven by repository evidence where execution is not necessary.

A critical item may not be downgraded to an assumption merely to reach PASS.

If an execution environment is unavailable, distinguish two cases:
- the missing execution is non-critical and static evidence is sufficient: PASS may still be possible, with limitations documented;
- a critical behavior such as migration-from-zero, transaction atomicity, or adapter operability cannot be validated and there is no equivalent evidence: do not claim full PASS. Use BLOCKED only if the cause is a true external dependency; otherwise leave the stage incomplete in project state and report the exact missing verification to the orchestrator.

## Phase 18 - Update project state and handoff

Preserve unknown state keys and append/update Stage 05 according to [references/project-state-contract.md](references/project-state-contract.md).

Record:
- status;
- evidence level;
- artifacts;
- commands/tests executed;
- schema/migration decisions;
- assumptions;
- risks/deferred items;
- compatibility amendments;
- next stage.

Handoff to Stage 06 must identify:
- persistence interfaces/adapters now available;
- transaction-sensitive use cases the API layer must call atomically;
- idempotency requirements for write endpoints;
- pagination/filter/sort constraints;
- database error classes that API mapping must handle;
- any remaining non-blocking operational risks.

# Required artifacts

When file tools are available, produce or update all applicable artifacts:
- database schema/migration files under repository convention;
- persistence adapter/repository implementation files;
- seed/reference-data files where required;
- database/integration tests needed to prove Stage 05 invariants;
- `docs/05-database-architecture.md`;
- `project-state.json`.

Do not create duplicate architecture files when an existing authoritative project convention already defines the correct location.

# Repair policy

When validation reveals a Stage 05 defect, repair it and rerun the affected checks before final status.

Do not stop after listing fix suggestions unless:
- the fix crosses the Stage boundary;
- the fix requires an external decision/credential;
- changing it would overwrite unrelated user work;
- the environment prevents safe modification.

After every repair, re-evaluate dependent migrations, tests, adapters, and documentation so evidence does not become stale.

# Stage boundary

Do not use this stage to:
- redesign product scope or UI;
- implement final HTTP/API client integration except the minimum needed to test persistence adapters;
- replace the Stage 04 domain architecture wholesale;
- implement final authentication/authorization flows beyond persistence structures required by approved interfaces;
- perform broad application security hardening unrelated to persistence;
- provision production infrastructure;
- deploy to production.

Security-, API-, or deployment-related findings that materially affect database design may be recorded as handoff risks without expanding this stage into those later stages.

# Completion markers

Emit exactly one status block at the end of the stage run.

On verified success:
`STAGE_05_STATUS: PASS`
`NEXT_STAGE: 06-api-integration`

On a true external blocker or failed prerequisite:
`STAGE_05_STATUS: BLOCKED`
`NEXT_STAGE: NONE`

Never emit PASS when the quality gate has not actually passed.
