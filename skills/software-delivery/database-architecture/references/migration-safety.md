# Migration Safety and Recovery

## Migration classes

Classify each change before implementation:

### Additive
New nullable column/table/index with no compatibility break. Usually lowest risk, but large-table index creation can still lock or consume resources.

### Backfill
Data transformation/population. Separate from schema DDL when volume, retryability, or lock duration is material.

### Tightening
Adding NOT NULL, UNIQUE, CHECK, FK, or narrower type. Validate/repair existing data before enforcement.

### Compatibility transition
Rename/type/API change requiring old and new application versions to coexist. Prefer expand-migrate-contract.

### Destructive
DROP/TRUNCATE/data-loss conversion. Require explicit evidence of migration/obsolescence and recovery.

## Expand-migrate-contract

When backward compatibility matters:
1. expand schema with new compatible structure;
2. deploy code capable of old + new representation if needed;
3. backfill in bounded/restartable batches;
4. verify parity/completeness;
5. switch reads/writes;
6. observe;
7. remove old structure in a later migration.

Do not combine these into one migration merely for convenience.

## Large table safety

For large/hot tables evaluate:
- whether DDL rewrites the table;
- lock type/duration;
- online/concurrent index support;
- transaction log/binlog/WAL growth;
- replication lag implications;
- backfill batching and throttling;
- timeout/retry behavior.

Use official engine/version documentation for uncertain behavior.

## NOT NULL transition

Safer sequence for populated tables:
1. add nullable column;
2. deploy write path populating it;
3. backfill existing rows;
4. verify zero NULL rows;
5. add/enforce constraint using engine-safe method;
6. remove temporary compatibility logic later.

## Unique constraint transition

Before adding uniqueness:
- run duplicate detection query;
- define deterministic duplicate resolution;
- repair data;
- add unique index/constraint;
- add application error mapping;
- test concurrent duplicate attempts.

## Foreign key transition

Validate orphan rows before adding the FK. Decide delete/update actions deliberately. Index the referencing side when workload/engine requires it.

## Rollback vs roll-forward

A down migration is not automatically safe. If rollback would delete newly written data or old code cannot understand new writes, prefer roll-forward recovery.

Document:
- restore/backup assumptions;
- forward fix path;
- deployment compatibility window;
- irreversible steps.

## Migration immutability

Treat migrations already applied in shared/prod environments as immutable unless the project's migration framework explicitly supports checksummed replacement safely. Fix with a new migration.

## Static risk scan

Run `scripts/migration_risk_scan.py <migration paths...>` after editing migrations. Review every HIGH finding manually. The scan is heuristic and does not replace engine-aware review.
