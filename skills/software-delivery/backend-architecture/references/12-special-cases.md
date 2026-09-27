# Special Cases

## Table of contents

1. Existing legacy database implementation
2. Existing microservices
3. Serverless/backend-as-functions
4. Event-driven systems
5. Monorepos
6. Regulated/high-assurance domains
7. Generated API clients/contracts
8. Partial or test-only backend

## 1. Existing legacy database implementation

Stage 04 may encounter a project that already has tables, migrations, ORM entities, or repositories even though the workflow says Stage 05 owns final persistence design.

Do not delete working persistence to make the workflow look clean.

Instead:

1. inventory the existing persistence implementation;
2. isolate database-specific logic behind application-owned ports where practical;
3. identify places where the existing schema leaks into business/transport code;
4. preserve behavior with tests;
5. record `existing_persistence_to_reconcile` in Stage 05 handoff;
6. defer physical schema redesign/migration decisions to Stage 05.

## 2. Existing microservices

Do not collapse established services merely because modular monolith is the default for greenfield design.

Assess:

- service ownership;
- deployability;
- contracts;
- data ownership;
- synchronous call chains;
- circular dependencies;
- shared database coupling;
- observability/retry behavior.

Improve Stage 04 boundaries inside and between services without speculative rewrites.

## 3. Serverless/backend-as-functions

Treat each function handler as transport/infrastructure. Extract shared domain/application logic where needed so business rules do not become duplicated across handlers.

Define cold-start/config/resource constraints when they affect architecture.

Do not create a long-running server just to match another architecture pattern.

## 4. Event-driven systems

When events already exist:

- identify owner/source of truth;
- version event contracts;
- define idempotent consumers;
- assume at-least-once delivery unless platform guarantees and application design prove otherwise;
- avoid dual writes without an atomic/outbox strategy requirement for Stage 05;
- record ordering and replay semantics.

## 5. Monorepos

Respect workspace boundaries. Determine whether domain/application contracts belong in the backend app or a shared package.

Do not put server-only secrets/configuration into packages bundled to clients.

Avoid bidirectional package dependencies.

## 6. Regulated/high-assurance domains

When validated requirements indicate legal, financial, health, identity, safety, or other high-assurance constraints:

- raise evidence quality;
- make authorization and audit semantics explicit;
- avoid silent coercion/normalization;
- model irreversible/destructive actions carefully;
- record retention/deletion requirements for Stage 05;
- use conservative defaults on ambiguity;
- block only on material legal/business decisions that cannot be safely inferred.

## 7. Generated API clients/contracts

If OpenAPI/GraphQL/protobuf or generated clients already define Stage 03 expectations:

- treat established schemas as compatibility evidence;
- do not hand-edit generated files unless the project requires it;
- update the source contract and regenerate when Stage 04 owns the contract change;
- record breaking changes explicitly.

## 8. Partial or test-only backend

If Stage 03 used mocks or a temporary backend:

- distinguish mock contracts from validated product contracts;
- preserve frontend-required semantics that are intentional;
- replace temporary in-memory implementations only to the extent Stage 04 needs stable ports/use cases;
- leave final persistence to Stage 05.
