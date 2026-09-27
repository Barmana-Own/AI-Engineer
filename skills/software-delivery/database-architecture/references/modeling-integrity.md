# Relational Modeling and Integrity

## Entity modeling

Model durable business concepts, not UI components. For each entity define responsibility, owner, identity, lifecycle, relationships, and invariants.

Prefer a surrogate primary key plus explicit unique business keys when business identifiers can change, are externally controlled, or are wider than practical join keys.

Do not add both UUID and numeric identifiers without a concrete reason. If public and internal identifiers differ, document the threat/modeling reason and lookup/index impact.

## Cardinality

For every relationship explicitly decide:
- 1:1, 1:N, N:M;
- mandatory vs optional parent;
- ownership vs reference;
- parent deletion behavior;
- whether historical rows must survive parent removal;
- whether tenant keys must be repeated to enforce scope.

Use join tables for N:M. If the relationship has attributes or lifecycle, treat the join as a first-class entity.

## Normalization

Target a coherent normalized model first. Avoid:
- comma-separated IDs;
- duplicated mutable attributes across tables without source-of-truth;
- unbounded generic key/value tables replacing real schema;
- JSON for core relational entities simply to avoid migrations.

Denormalization is allowed only when the query/performance benefit and synchronization method are documented.

## Constraint matrix

For every business invariant record:
- rule;
- table/columns;
- database enforcement;
- application enforcement;
- concurrency behavior;
- test that proves it.

Examples:
- one email per tenant -> composite unique constraint;
- quantity cannot be negative -> check constraint plus domain validation;
- child requires parent -> NOT NULL foreign key;
- only one active default address -> filtered/functional strategy or transactional enforcement depending on engine.

## Nullability and defaults

`NULL` must mean something explicit: unknown, not applicable, not yet assigned, or absent. Do not use NULL and empty string interchangeably.

Avoid defaults that hide missing required business input. Use database defaults for true infrastructure defaults such as creation timestamps only when consistent with application behavior.

## Money and quantities

Use fixed precision/decimal/integer minor units according to requirements. Record currency/unit explicitly when not globally fixed. Do not use floating-point types for exact financial values.

## Time

Define:
- storage timezone policy;
- instant vs local-date/local-time semantics;
- precision requirements;
- created/updated/deleted timestamps;
- validity intervals and boundary inclusivity.

A birthday or business calendar date is not the same data type as an event timestamp.

## State and enums

Use the least fragile representation supported by engine and evolution needs. Ensure invalid states are rejected somewhere durable. Do not create a database enum if frequent value evolution would make migrations operationally unsafe without considering alternatives.

## Tenant isolation

For multi-tenant systems, identify tenant-owned tables and ensure every relevant unique key/query is scoped correctly. Test for cross-tenant reads and writes at the adapter level.
