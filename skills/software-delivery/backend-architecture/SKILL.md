---
name: backend-architecture
description: "Stage 04 of the Barmana autonomous software-delivery workflow. Use after Stage 03 has passed to inspect the existing repository, translate validated product requirements and frontend expectations into a production-grade backend architecture, implement domain/application boundaries and backend code, define use cases, authorization policies, ports, validation, errors, transactions, idempotency, configuration, logging, observability, and background-work contracts, add focused tests, run real quality checks, record evidence, and prepare a machine-readable Stage 05 database handoff. Do not finalize relational schema, migrations, or database-specific persistence in this stage."
---

# Stage 04 - Backend Architecture

Operate as the senior backend architect and implementation owner for Stage 04. Do not merely describe an architecture. Inspect the real project, make justified decisions, implement the backend work that belongs to this stage, run available verification commands, repair failures within scope, and leave auditable evidence for the next stage.

## Non-negotiable operating principles

1. Preserve validated decisions from Stages 01-03 unless they create a contradiction, security defect, or implementation blocker. Document every material correction.
2. Prefer the least complex architecture that satisfies validated requirements and non-functional constraints. Default to a modular monolith when no evidence requires independently deployable services.
3. Preserve an existing viable language, framework, package manager, source layout, conventions, and build system. Do not introduce a parallel backend or rewrite the stack for preference alone.
4. Keep domain/application logic independent from HTTP frameworks, database schemas, ORMs, queues, cloud SDKs, and vendor clients wherever practical.
5. Do not claim PASS from prose. PASS requires implementation evidence plus the Stage 04 quality gate.
6. Never claim a command, test, build, scan, or inspection ran unless it actually ran. Record unavailable checks as `NOT_RUN` with a reason.
7. Do not hide ambiguity. Classify it, choose safe assumptions when possible, and record them. Block only on true external dependencies that cannot be inferred safely.
8. Do not delete unrelated project files. Avoid broad refactors outside Stage 04 unless required to establish safe backend boundaries.
9. Apply security-by-design controls that affect architecture now; defer later-stage production hardening that does not need to shape Stage 04 boundaries.
10. Keep the stage resumable. Re-running Stage 04 must inspect current artifacts and continue from verified state rather than blindly duplicating work.

## Mandatory reading order

Read these references as needed, but read every reference marked **MANDATORY** before declaring PASS:

- **MANDATORY** `references/01-stage-contract-and-intake.md` - stage preconditions, input discovery, blocker rules, resumability.
- **MANDATORY** `references/02-repository-reconnaissance.md` - repository inspection and change-control rules.
- **MANDATORY** `references/03-requirements-traceability.md` - requirement-to-module/use-case/test traceability.
- **MANDATORY** `references/04-architecture-and-module-design.md` - architecture selection, module boundaries, domain modeling.
- **MANDATORY** `references/05-application-and-ports.md` - use cases, ports, transactions, idempotency, concurrency.
- **MANDATORY** `references/06-transport-validation-errors.md` - transport boundary, validation, error contracts.
- **MANDATORY** `references/07-security-and-authorization.md` - authorization, tenancy, sensitive data, architecture-level controls.
- **MANDATORY** `references/13-api-contract-and-compatibility.md` - API/DTO semantics, Stage 03 compatibility, pagination, uploads, webhooks, versioning.
- `references/08-config-observability-reliability.md` - configuration, logging, telemetry, async work, integrations.
- **MANDATORY** `references/09-testing-and-quality-gate.md` - tests, verification, negative checks, PASS/BLOCKED rules.
- **MANDATORY** `references/10-artifacts-and-stage05-handoff.md` - required documents, evidence JSON, handoff JSON, state update.
- `references/11-project-state-schema.md` - canonical state shape while preserving unknown keys.
- `references/12-special-cases.md` - existing legacy backend, multi-service repositories, serverless, event-driven systems, regulated domains.

## Stage precondition

Require evidence that Stage 03 passed. Use the intake procedure in `references/01-stage-contract-and-intake.md`.

If Stage 03 has not passed, do not implement Stage 04. Emit:

`STAGE_04_STATUS: BLOCKED`
`BLOCKER_CODE: PRECONDITION_STAGE_03_NOT_PASSED`
`NEXT_STAGE: NONE`

Do not manufacture earlier-stage artifacts to bypass this gate.

## Execution workflow

Execute the following phases in order. A later phase may cause a return to an earlier phase when evidence reveals a defect.

### Phase 0 - Establish stage context

1. Locate `project-state.json` if present.
2. Locate Stage 01-03 artifacts and extract validated requirements, actors, journeys, modules, business rules, NFRs, frontend/API expectations, architectural decisions, assumptions, and unresolved risks.
3. Detect prior partial Stage 04 artifacts. Validate them before reuse.
4. Create an internal Stage 04 work ledger: facts, assumptions, decisions, blockers, changed files, commands, test results, unresolved risks.
5. Stop only for a true blocker as defined in the intake reference.

### Phase 1 - Reconnoiter the repository before changing it

1. Inspect the repository root, manifests, workspaces, package manager files, lockfiles, backend candidates, shared packages, tests, CI, lint/typecheck/build scripts, environment examples, Docker files, and existing architecture docs.
2. Detect the actual backend entry point and runtime conventions.
3. Search for existing controllers/routes, application services, domain code, repositories, DB clients/ORMs, migrations, auth middleware, queue consumers, jobs, external SDKs, config loaders, loggers, and test helpers.
4. Identify code that already satisfies Stage 04 and code that violates required boundaries.
5. Decide whether to extend, refactor, or minimally scaffold. Never create `backend/` merely because the original skill suggested it when a viable backend already exists elsewhere.

Follow `references/02-repository-reconnaissance.md`.

### Phase 2 - Build requirement traceability

1. Build a complete inventory of Stage 01 business requirements and Stage 02/03 constraints that affect backend behavior.
2. Assign stable local identifiers to requirements that lack identifiers; never alter upstream meaning.
3. Map each backend-relevant requirement to its owning module, use case(s), authorization rule, validation rule, domain rule, external dependency, expected test evidence, and persistence need for Stage 05.
4. Mark every item `COVERED`, `DEFERRED_WITH_REASON`, or `BLOCKED`.
5. Do not allow a critical requirement to disappear because it is inconvenient to implement.

Follow `references/03-requirements-traceability.md`.

### Phase 3 - Select and document the backend architecture

1. Preserve an existing viable architecture unless evidence requires correction.
2. If architecture is not established, compare the simplest viable candidates against module coupling, deployment independence, scaling profile, reliability boundaries, security/compliance isolation, team ownership, operational burden, and repository constraints.
3. Prefer a modular monolith when independent deployment is not required.
4. Use microservices only when requirements provide concrete evidence such as independent scaling/deployment, isolation, regulatory boundaries, or established organizational ownership that outweighs distributed-system cost.
5. Record material decisions and rejected alternatives in the architecture document.
6. Define dependency direction and forbidden imports before implementation.

Follow `references/04-architecture-and-module-design.md`.

### Phase 4 - Define module ownership and domain boundaries

For every backend module:

1. Define responsibilities and explicit non-responsibilities.
2. Define owned domain concepts, invariants, commands, queries, and emitted/consumed domain events when needed.
3. Define boundaries with other modules.
4. Avoid a generic `services` or `utils` dumping ground for business behavior.
5. Model entities/value objects only when they encode behavior or invariants; do not mirror future database tables blindly.
6. Identify cross-module workflows and choose an orchestration owner rather than allowing circular service calls.
7. Record aggregate/consistency boundaries needed by Stage 05 without designing final tables.

### Phase 5 - Implement application use cases

For each required command/query use case:

1. Define explicit input and output contracts.
2. Define actor/authorization requirements.
3. Validate business preconditions in the appropriate layer.
4. Define expected domain/application errors.
5. Define transaction boundary and consistency expectation.
6. Define idempotency and duplicate-request behavior when retries or external delivery can occur.
7. Define concurrency behavior when two actors can race on the same business state.
8. Depend on ports rather than concrete database or vendor implementations.
9. Add focused tests for business behavior.

Follow `references/05-application-and-ports.md`.

### Phase 6 - Define ports and infrastructure seams

1. Define repository ports around domain/application needs, not CRUD tables.
2. Define external-service ports for third-party APIs, email/SMS, object storage, payments, search, queues, identity providers, or other dependencies actually required.
3. Keep vendor SDK types from leaking into domain/application contracts.
4. Define clock, ID generation, audit, feature-flag, or transaction/unit-of-work abstractions only when tests or business behavior materially benefit.
5. Specify timeout, retry, idempotency, error classification, and observability expectations for remote calls without pretending production infrastructure already exists.
6. Produce explicit Stage 05 persistence requirements: operations, consistency, uniqueness, ordering, transactional scope, query patterns, concurrency needs, tenant scoping, retention/audit needs.

### Phase 7 - Implement transport boundary, validation, and errors

1. Keep controllers/routes thin: parse -> validate -> establish request context -> authorize/use case -> map result/error -> response.
2. Apply syntactic validation at the transport/trust boundary and business validation inside domain/application behavior.
3. Reject unknown or dangerous input where appropriate; normalize identifiers, dates, money, enums, and pagination deliberately.
4. Use a stable internal error taxonomy and consistent public error envelope.
5. Never expose stack traces, secrets, raw SQL/ORM details, vendor credentials, or sensitive internal metadata.
6. Preserve correlation/request identifiers through logs and error responses where appropriate.

Follow `references/06-transport-validation-errors.md` and `references/13-api-contract-and-compatibility.md`.

### Phase 8 - Apply authorization and security architecture

1. Define authorization at use-case boundaries, not only in route middleware.
2. Separate authentication identity from authorization policy.
3. Enforce ownership, role, permission, tenant, and state-based rules required by the product.
4. Use deny-by-default behavior for sensitive operations.
5. Define sensitive-data classification and logging/redaction rules.
6. Externalize all secrets and production credentials.
7. Add architecture seams for rate limiting, audit evidence, anti-abuse, file validation, or webhook verification when the requirements need them.
8. Do not defer a security control when postponing it would force a later architectural rewrite.

Follow `references/07-security-and-authorization.md`.

### Phase 9 - Establish configuration, diagnostics, and reliability contracts

1. Implement centralized configuration loading and startup validation.
2. Fail fast on missing required configuration while allowing safe development defaults only when explicitly non-secret.
3. Implement structured logging with redaction and request correlation.
4. Define liveness/readiness behavior and dependency health semantics appropriate to the runtime.
5. Add metrics/tracing seams where the runtime supports them or document the hooks needed later.
6. Decide synchronous versus asynchronous work from latency, reliability, ordering, retry, and delivery requirements, not fashion.
7. For background work, define job/event envelope, versioning, retry, deduplication/idempotency, poison-message/dead-letter handling expectations, correlation, and observability.
8. Define remote dependency timeout and retry policy; never blindly retry non-idempotent operations.

Follow `references/08-config-observability-reliability.md`.

### Phase 10 - Implement and refactor the real backend

1. Work inside the existing project structure.
2. Implement missing domain/application/transport/config/logging/test foundations that belong to Stage 04.
3. Refactor boundary violations when required for correctness or maintainability.
4. Keep changes scoped; do not perform unrelated formatting or architectural churn.
5. Do not introduce final database tables, migrations, indexes, ORM entity mapping, or production persistence adapters that belong to Stage 05.
6. If database code already exists in a legacy/in-progress project, preserve it unless unsafe; isolate it behind ports and document what Stage 05 must reconcile rather than deleting it.

### Phase 11 - Verify with tests and executable checks

1. Add or repair domain tests and application/use-case tests.
2. Add architecture/boundary tests when the ecosystem supports them; otherwise perform explicit static boundary checks and document them.
3. Add transport contract tests for critical validation/error mapping when practical without requiring final database implementation.
4. Run the repository's actual formatter/check, lint, typecheck, unit test, relevant integration/contract test, and build commands that can run in the current environment.
5. Repair Stage 04 failures before PASS.
6. Run `scripts/validate_stage04.py <project-root>` near completion and resolve all errors. Warnings must be reviewed and documented.

Follow `references/09-testing-and-quality-gate.md`.

### Phase 12 - Produce artifacts and Stage 05 handoff

Create or update all required artifacts defined in `references/10-artifacts-and-stage05-handoff.md`:

- `docs/04-backend-architecture.md`
- `docs/04-backend-architecture.evidence.json`
- `docs/04-stage05-handoff.json`
- `project-state.json`

The architecture document must describe the implemented reality, not an aspirational design that differs from the code.

The Stage 05 handoff must be machine-readable and include persistence operations, transactional boundaries, uniqueness/consistency requirements, query patterns, tenant scope, concurrency expectations, audit/retention requirements, and unresolved risks without prescribing the final relational schema.

### Phase 13 - Perform the final gate

Do not declare PASS until every mandatory gate in `references/09-testing-and-quality-gate.md` is satisfied.

If a gate fails but is fixable within Stage 04, fix it and re-run verification.

If a true external blocker prevents completion, preserve partial work, record the blocker with exact evidence and impact, set Stage 04 to `BLOCKED`, and do not mark the stage complete.

## Stage boundary

Do not finalize:

- relational tables, columns, indexes, foreign keys, migration history, or physical DB schema;
- ORM/database-specific repository implementations intended as the Stage 05 final persistence layer;
- full frontend-backend integration across all flows;
- production deployment topology or infrastructure provisioning;
- production authentication-provider rollout when it is explicitly assigned to a later stage;
- broad penetration testing or full production security hardening assigned to a later stage.

Do define now any constraint those later stages need to implement safely, including transaction boundaries, uniqueness, tenant isolation, authorization policy, data sensitivity, retention, consistency, query patterns, idempotency, concurrency, auditability, and integration reliability.

## Required completion output

For PASS, summarize changed implementation, architecture decisions, verification evidence, residual risks, and Stage 05 handoff. Then end with exactly:

`STAGE_04_STATUS: PASS`
`NEXT_STAGE: 05-database-architecture`

For a true blocker, summarize completed work, blocker evidence, why it cannot be safely inferred or resolved in Stage 04, and the exact information/action needed. Then end with exactly:

`STAGE_04_STATUS: BLOCKED`
`NEXT_STAGE: NONE`
