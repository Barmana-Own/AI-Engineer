# Indexing and Query-Plan Review

## Query-first indexing

Create indexes only after identifying query shapes from repository methods, API requirements, background jobs, reports, and uniqueness rules.

For each high-value query record:
- table(s);
- predicates;
- join columns;
- tenant scope;
- ordering;
- pagination method;
- expected selectivity/cardinality;
- candidate index;
- observed query plan when executed.

## Composite indexes

Order columns intentionally. Equality predicates often precede range/sort columns, but verify engine behavior and actual query plan. An index `(tenant_id, status, created_at)` is not equivalent to separate indexes on those columns.

## Uniqueness

Prefer a unique constraint/index for real uniqueness invariants. For soft-delete uniqueness, design the strategy explicitly because NULL/partial-index behavior differs across engines.

## Foreign keys

Confirm whether the selected engine automatically indexes referenced/referencing columns and whether the workload needs an explicit index. Do not assume identical behavior across engines.

## Pagination

For large datasets, evaluate keyset/cursor pagination for stable high-volume paths. Offset pagination may be acceptable for small/admin datasets but must not be the unexamined default for deep pages.

## Redundancy

Look for:
- left-prefix duplicates;
- identical indexes with different names;
- indexes superseded by unique constraints;
- indexes never used by a query path;
- excessive indexing on high-write tables.

## EXPLAIN evidence

When tools/data permit, capture plans for the most important/risky queries. Check for unexpected full scans, large row estimates, filesort/temp structures where relevant, and whether the intended index is selected.

Do not optimize solely to force a specific index. Query planner choices may be correct based on cardinality.

## N+1

Repository/ORM adapters must be reviewed for N+1 behavior. Use joins, eager loading, batching, or explicit aggregate queries as appropriate. A correct schema can still produce an unusable persistence layer through inefficient adapter code.
