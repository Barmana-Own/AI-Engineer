# Stage 05 Validation Matrix and Quality Gate

The quality gate is evidence-based. Mark each applicable item `PASS`, `FAIL`, `NOT_RUN`, `N/A`, or `UNVERIFIED`, with evidence.

## A. Prerequisite and traceability - critical

- Stage 04 PASS evidence exists.
- Every Stage 04 repository port is implemented or explicitly mapped.
- Every material business invariant has an enforcement/test mapping.
- Database/ORM/migration technology matches approved architecture or has a documented amendment.

## B. Schema integrity - critical

- primary keys and business keys are coherent;
- required foreign keys/cardinalities are enforced;
- nullability/defaults reflect semantics;
- uniqueness rules are database-backed where races matter;
- check/domain constraints exist where appropriate;
- cascade/delete behavior matches lifecycle;
- tenant/ownership scope is represented safely.

## C. Migrations - critical

- migrations are deterministic and ordered;
- existing applied migrations were not unsafely rewritten;
- destructive/locking risks are documented;
- migration-from-zero succeeds on a disposable database when executable;
- data backfills/tightening changes have safe sequencing;
- recovery/roll-forward strategy exists for risky changes.

## D. Persistence adapters - critical

- production wiring uses real persistence;
- repository method behavior matches Stage 04 contracts;
- transaction context works for multi-repository invariants;
- tenant/soft-delete filters are correct;
- database errors are translated where required;
- representative CRUD/query operations are verified.

## E. Transactions and concurrency - critical when applicable

- multi-row invariants have transaction boundaries;
- uniqueness races have durable enforcement;
- lost-update/capacity/quota races are handled;
- idempotent write requirements have durable deduplication;
- forced failure proves atomic rollback;
- concurrent test exists for business-critical race paths when executable.

## F. Indexes/performance - critical for known hot paths

- query-to-index matrix exists;
- uniqueness indexes match invariants;
- hot joins/filters/sorts have justified indexes;
- redundant speculative indexes were removed/avoided;
- high-risk plans were inspected when tooling/data allow;
- unbounded list/N+1 patterns are not introduced by adapters.

## G. Lifecycle/audit/seed

- delete/retention behavior is explicit;
- audit requirements are distinct from timestamps;
- seed data contains no production secrets or real personal data;
- test fixtures are deterministic;
- production seed behavior is safe by default.

## H. Documentation/state - critical

- `docs/05-database-architecture.md` follows required structure;
- actual command results are recorded truthfully;
- assumptions/risks/deferred items are explicit;
- `project-state.json` preserves existing unrelated keys;
- Stage 06 handoff identifies transaction/idempotency/error/pagination implications.

## PASS rule

Stage 05 may PASS only when all applicable critical items PASS or are N/A with justification, and no unresolved defect can violate data integrity or prevent the Stage 04 persistence contract from functioning.

`NOT_RUN`/`UNVERIFIED` on a critical item prevents PASS unless equivalent direct evidence proves the behavior without execution.

Do not use BLOCKED for ordinary implementation failures; fix them. Use BLOCKED for failed prerequisites or true external dependencies that prevent safe completion.
