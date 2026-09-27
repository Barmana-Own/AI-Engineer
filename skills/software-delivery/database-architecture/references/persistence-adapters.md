# Persistence Adapter Implementation

## Port coverage

Create a port-to-adapter matrix. Every Stage 04 repository method must map to a concrete implementation or an explicit, justified non-persistence path.

For each method verify:
- parameters are translated correctly;
- tenant/owner scope is applied;
- soft-delete visibility is correct;
- ordering/pagination is deterministic;
- empty/not-found behavior matches the port;
- database errors are translated as expected;
- transaction context can propagate when required.

## Domain separation

Do not leak ORM entities, mutable query objects, or engine-specific exceptions across the domain boundary unless Stage 04 intentionally uses that architecture.

Map persistence representations to domain values explicitly where type/semantic differences exist.

## Transactions

Avoid starting independent nested transactions inside repository methods if the use case requires a shared transaction across repositories. Follow the project's unit-of-work/transaction-context pattern or introduce the minimum coherent mechanism if Stage 04 left one abstract.

## Error translation

Recognize and translate at least the database errors relevant to approved behavior:
- unique violation;
- foreign-key violation;
- optimistic-version conflict;
- not found when represented by affected-row count;
- serialization/deadlock retry cases where supported.

Do not expose raw SQL/connection details to end-user error messages.

## Production wiring

Find the actual dependency-injection/container/bootstrap path. Ensure production runtime resolves the real database adapter, not an in-memory stub.

An in-memory implementation may remain for unit tests. Do not delete it unless it is truly obsolete and unreferenced.

## Connection lifecycle

Respect application lifecycle:
- initialize pool/client once at the proper boundary;
- close gracefully on shutdown/test teardown;
- do not create a new connection pool per request;
- ensure test isolation does not leak transactions/connections.
