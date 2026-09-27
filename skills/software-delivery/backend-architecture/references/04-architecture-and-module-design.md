# Architecture and Module Design

## Table of contents

1. Architecture decision hierarchy
2. Complexity budget
3. Module boundaries
4. Domain modeling rules
5. Cross-module coordination
6. Dependency rules
7. Decision record minimum

## 1. Architecture decision hierarchy

Choose architecture in this order:

1. Preserve a viable existing architecture.
2. Satisfy validated functional and non-functional requirements.
3. Minimize operational and cognitive complexity.
4. Maximize testability and boundary clarity.
5. Preserve future change paths that are already likely from evidence.

Do not optimize for hypothetical scale or fashionable patterns.

## 2. Complexity budget

Default preference:

1. well-structured single application;
2. modular monolith with explicit internal module boundaries;
3. separately deployable services only when justified.

Require concrete evidence before adding distributed-system complexity. Evidence can include:

- independent deployment cadence that is materially valuable;
- independent scaling profile with demonstrated/credible load difference;
- security/regulatory isolation;
- strong organizational ownership boundaries;
- failure isolation requirement;
- different runtime constraints that cannot be met cleanly in one deployable.

If those conditions do not exist, prefer a modular monolith.

## 3. Module boundaries

Each module must define:

- purpose;
- owned business capabilities;
- owned domain concepts;
- public application contracts;
- inbound dependencies;
- outbound dependencies;
- forbidden dependencies;
- data/persistence needs for Stage 05;
- events/messages if any;
- security/tenant boundary implications.

Healthy modules have high internal cohesion and low external coupling.

Avoid modules named only by technical layers such as `controllers`, `services`, or `models` at the top-level when that obscures business ownership. Technical layers may exist inside a business module or coherent application structure.

## 4. Domain modeling rules

Use entities/value objects/domain services only when they carry meaningful behavior, invariants, identity, or domain semantics.

Do not create anemic wrappers around every primitive without benefit.

Model carefully:

- identifiers;
- money and currency;
- percentages/rates;
- dates, instants, durations, and timezone semantics;
- state/status transitions;
- quantities and units;
- email/phone/URL only when validation semantics matter;
- immutable value objects for concepts with invariants.

Do not use floating-point types for exact monetary calculations when the language/runtime provides safer decimal/integer-minor-unit options.

Do not let HTTP request DTOs or future ORM record shapes become the domain model by default.

## 5. Cross-module coordination

For a workflow spanning modules:

1. identify the use case that owns orchestration;
2. keep each module's invariant enforcement inside its boundary;
3. avoid bidirectional service calls and circular imports;
4. use internal application contracts or events only when they reduce coupling;
5. define consistency expectations explicitly.

Do not introduce asynchronous events merely to avoid a normal in-process method call.

## 6. Dependency rules

Prefer dependency direction:

`transport/infrastructure -> application -> domain`

Ports/interfaces may be owned by the layer that consumes the capability.

Domain/application code should not import:

- HTTP framework types;
- ORM clients/entities;
- concrete queue clients;
- cloud SDK clients;
- vendor-specific API response types;
- process-global environment access scattered through business logic.

Exceptions require an explicit rationale and should remain localized.

## 7. Decision record minimum

For each material architecture decision, capture:

- decision;
- context/requirement evidence;
- alternatives considered;
- why selected;
- trade-offs/costs;
- reversibility;
- downstream Stage 05 implications.
