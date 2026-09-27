---
name: api-integration
description: "Stage 06 of the Barmana autonomous full-stack delivery workflow. Use only after Stage 05 has passed and the project is ready to finalize API contracts and connect the real frontend to the real backend. Perform production-grade API inventory, requirement-to-endpoint traceability, request/response and error contract design, pagination/filtering/sorting, idempotency, concurrency and file-transfer semantics, OpenAPI synchronization, backend route/controller integration, centralized frontend API-client integration, production-mock removal, contract/integration/E2E validation, and evidence-based quality gating before Stage 07 authentication and authorization hardening."
---

# Stage 06 - API Design and Frontend-Backend Integration

Operate as the senior API/integration engineer responsible for making the application behave as one real system. Do not treat this stage as documentation-only work. Inspect the repository, make scoped implementation changes, execute available validation commands, repair failures caused by this stage, and prove that core journeys travel from the real UI through the real API into the real persistence layer and back.

## 1. Stage contract

Treat this skill as Stage 06 in a strict twelve-stage workflow.

Required predecessor:
- Stage 05 must be recorded as `PASS`.

Required successor on success:
- `07-authentication-authorization`.

Never mark this stage `PASS` because documents were produced, routes exist, or a build succeeds. PASS requires the quality gate and evidence rules in this skill to succeed.

Preserve valid decisions and artifacts from earlier stages. Change an earlier decision only when one of these conditions is true:
- it contradicts an explicit requirement;
- it creates a security, correctness, integrity, or operability defect;
- it prevents the current stage from being implemented correctly;
- the repository already contains a newer authoritative implementation.

When correcting an earlier-stage decision, record the reason and affected requirement IDs in `docs/06-api-design.md` and `project-state.json`.

## 2. Mandatory references

Read these references only when their subject becomes relevant, but treat their rules as binding for Stage 06:

- `references/execution-workflow.md` - exact phase-by-phase execution procedure, checkpoints, branching rules, and evidence requirements.
- `references/api-contract-standards.md` - API resource modeling, HTTP semantics, schemas, versioning, pagination, filtering, sorting, search, bulk operations, caching, concurrency, and file transfer.
- `references/error-reliability-standards.md` - error envelope, dependency failures, timeouts, retries, idempotency, duplicate handling, correlation, and safe observability.
- `references/frontend-integration-standards.md` - centralized client architecture, environment configuration, DTO mapping, request lifecycle, cancellation, user-facing error states, and mock removal.
- `references/testing-quality-gate.md` - test matrix, required evidence, quality-gate scoring, blocker rules, and PASS/BLOCKED decision procedure.
- `references/project-state-contract.md` - deterministic `project-state.json` read/update rules and Stage 06 state schema.
- `references/artifact-template.md` - mandatory structure and tables for `docs/06-api-design.md`.
- `references/performance-operability-standards.md` - bounded-work, query, payload, transaction, dependency fan-out, logging, and observability sanity checks.

Use the bundled scripts where available:
- `scripts/validate_project_state.py`
- `scripts/scan_production_mocks.py`
- `scripts/validate_stage06_artifacts.py`

The scripts support judgment; they do not replace repository-specific tests or direct inspection.

## 3. Non-negotiable operating rules

### 3.1 Inspect before editing

Before changing code:
1. Locate the repository root and existing project instructions.
2. Read `project-state.json` if present.
3. Identify Stage 01-05 artifacts and requirement IDs.
4. Identify frontend, backend, persistence, shared types, tests, OpenAPI/docs, environment configuration, and build tooling.
5. Capture a baseline of repository state and available validation commands.
6. Identify uncommitted user changes and preserve them.

Do not overwrite, reset, revert, discard, or reformat unrelated user work.

### 3.2 Prefer repository conventions

Do not re-platform a working project merely to impose a preferred architecture. Reuse the established framework, package manager, directory conventions, validation library, HTTP client, test runner, OpenAPI tooling, logging framework, and code style unless they are objectively inadequate for a Stage 06 requirement.

### 3.3 Evidence over assertion

Never claim that a route, integration, test, build, migration, or E2E flow works unless it was actually inspected or executed. Distinguish:
- `verified`: directly executed or inspected with sufficient evidence;
- `implemented-not-executable`: implemented but blocked from runtime validation by a real external dependency;
- `assumed`: a non-critical inference recorded explicitly;
- `blocked`: execution cannot safely continue without unavailable external information or access.

### 3.4 Do not weaken security

Stage 07 owns authentication and authorization hardening, but Stage 06 must preserve existing protections.

Never:
- remove or bypass existing authentication/authorization to make integration easier;
- disable CSRF, origin, session, token, permission, upload, rate-limit, or validation controls already present;
- expose secrets in frontend code, documentation, logs, examples, or OpenAPI;
- create a production switch that can silently enable fake authentication or fake persistence.

If authentication already exists, integrate through it as-is and document Stage 07 follow-up items separately.

### 3.5 Minimize production mocks

Remove only mock behavior reachable from a production execution path.

Preserve legitimate:
- unit/integration test mocks;
- fixtures;
- deterministic test doubles;
- Storybook/demo data that is build-isolated from production;
- development-only adapters that cannot be selected in production.

Do not delete a mock solely because its filename contains `mock`, `fake`, `fixture`, `stub`, or `sample`.

### 3.6 Resolve ambiguity professionally

For non-critical ambiguity, choose the safest reasonable interpretation, record the assumption, and continue.

Block only for a true external dependency such as:
- credentials required to execute an essential third-party integration;
- a private API specification that cannot be inferred;
- mandatory legal/business approval;
- inaccessible infrastructure required to prove a hard acceptance criterion;
- mutually contradictory requirements that materially change contract behavior and cannot be resolved from repository evidence.

Do not block for minor naming, formatting, or implementation choices a senior engineer can safely decide.

## 4. Preconditions and entry gate

Do not begin implementation until all entry checks are performed.

1. Read `project-state.json`.
2. Verify Stage 05 is exactly `PASS` using `references/project-state-contract.md`.
3. Verify required Stage 05 persistence artifacts still exist or that equivalent current artifacts are present.
4. Collect requirement IDs and core user journeys from earlier-stage artifacts.
5. Confirm the backend has callable application/use-case boundaries and persistence access for flows expected in this stage.
6. Confirm the frontend has identifiable integration points for those flows.
7. Record baseline validation commands and baseline failures.

If Stage 05 is not PASS, stop with:
`STAGE_06_STATUS: BLOCKED`
`NEXT_STAGE: NONE`

Document the exact predecessor defect. Do not silently repair an entire missing Stage 05 inside Stage 06.

## 5. Required execution sequence

Follow the complete workflow in `references/execution-workflow.md`. The high-level order is mandatory:

1. Establish baseline and repository map.
2. Build requirement and journey inventory.
3. Build requirement-to-API traceability matrix.
4. Classify API surface and preserve existing architectural style.
5. Design or normalize contract semantics.
6. Define error and reliability semantics.
7. Define OpenAPI synchronization strategy.
8. Implement backend transport adapters without duplicating domain logic.
9. Implement centralized real frontend integration.
10. Eliminate production-reachable mock paths.
11. Validate contract, integration, persistence, and UI flows.
12. Repair Stage 06 regressions.
13. Produce artifacts and evidence.
14. Run the final quality gate.
15. Update `project-state.json` atomically.

Do not skip directly from contract design to PASS.

## 6. Traceability requirement

Maintain a Stage 06 traceability matrix for every core requirement/user journey that needs an API operation.

Minimum columns:
- requirement ID;
- user journey/use case;
- frontend entry point;
- API operation/method/path;
- request DTO/schema;
- backend controller/handler;
- application use case/service;
- persistence or external dependency;
- response DTO/schema;
- frontend consumer/state update;
- validation/test evidence;
- status (`covered`, `partial`, `blocked`, `not-applicable`).

No core flow may be considered complete if the matrix stops at an endpoint and does not trace through persistence/external effects and the frontend consumer where applicable.

## 7. API contract requirements

Apply `references/api-contract-standards.md`.

At minimum, explicitly decide and implement where relevant:
- transport style and compatibility with existing architecture;
- resource/action naming;
- HTTP method semantics;
- success status codes;
- validation status codes;
- not-found/conflict semantics;
- request and response schemas;
- optionality and nullability;
- ID representation;
- date/time/timezone representation;
- money/decimal representation;
- enum compatibility;
- pagination and hard limits;
- filtering, sorting, search, and field selection;
- bulk-operation semantics;
- optimistic concurrency/precondition semantics where races matter;
- idempotency for retry-prone commands;
- file upload/download semantics;
- caching/ETag decisions where useful;
- external integration callback/webhook semantics;
- API versioning decision;
- backward-compatibility implications.

Do not invent complexity that the product does not need, but do not leave behavior undefined when undefined behavior creates correctness risk.

## 8. OpenAPI contract

For HTTP APIs, maintain an OpenAPI document in the repository's established location, defaulting to `docs/openapi.yaml` when no convention exists.

Choose one synchronization model and record it:
- `contract-first`: OpenAPI is authoritative and implementation follows it; or
- `code-first`: implementation metadata/types are authoritative and OpenAPI is generated/derived.

Do not maintain two independent authoritative schemas.

OpenAPI must cover all Stage 06 production HTTP operations and accurately represent:
- parameters;
- request bodies;
- response bodies;
- status codes;
- validation/error responses;
- pagination metadata;
- upload/download media types where applicable;
- idempotency or conditional headers where applicable;
- deprecation/versioning markers where applicable.

If OpenAPI tooling exists, run its validation/generation/diff checks. If no validator exists, perform structural inspection and record that limitation.

## 9. Backend integration rules

Transport code must remain an adapter around earlier-stage application/domain logic.

A route/controller/handler should normally:
1. parse transport input;
2. validate transport-level structure;
3. map authenticated/request context if already available;
4. call an application use case/service;
5. map domain/application result to transport DTO/status;
6. normalize errors through the common error model;
7. emit safe structured telemetry where existing project conventions require it.

Do not duplicate business rules in controllers merely to make an endpoint work.

Verify backend paths reach Stage 05 persistence or the intended external adapter for flows that require side effects.

## 10. Frontend integration rules

Apply `references/frontend-integration-standards.md`.

Production frontend code must use real backend operations through a consistent integration layer. Avoid ad-hoc `fetch`/HTTP calls scattered through components when the project architecture supports a shared client/service layer.

At minimum verify:
- API base URL/configuration is environment-driven;
- no production secret is bundled into the client;
- request serialization matches backend schemas;
- query serialization is stable;
- response DTOs are mapped consistently;
- server errors are normalized;
- loading, empty, validation, conflict, dependency-failure, and retry states are represented where relevant;
- request cancellation/stale-response handling exists where UI races can occur;
- uploads use real progress/error behavior when required;
- frontend production paths no longer depend on fixture data for integrated journeys.

## 11. Error and reliability rules

Apply `references/error-reliability-standards.md`.

Use one stable machine-readable error model. Error payloads must not leak stack traces, SQL text, secrets, internal file paths, tokens, or sensitive infrastructure details.

For retry-prone mutations, explicitly define duplicate behavior. Payments, submissions, provisioning, order creation, webhook/callback processing, and similar commands must not rely on "the user probably will not click twice".

For external dependencies, define:
- timeout behavior;
- retry eligibility;
- maximum retry policy when owned by this layer;
- non-retryable conditions;
- client-visible failure classification;
- correlation/request IDs when existing observability supports them.

## 12. Performance and operability sanity

Apply `references/performance-operability-standards.md` to core production API paths. Stage 06 need not perform premature optimization, but it must not ship obvious unbounded queries, N+1 behavior in core paths, uncontrolled dependency fan-out, unbounded payloads/files, indefinite network waits, or transaction scopes that span slow network calls without architectural justification. Preserve existing logging, metrics, tracing, and health conventions for new routes.

## 13. Validation and test obligations

Use `references/testing-quality-gate.md`.

Run the strongest available relevant checks, typically including:
- formatter/check mode when established;
- lint;
- frontend typecheck;
- backend typecheck/compile;
- unit tests affected by Stage 06;
- API/contract tests;
- integration tests;
- OpenAPI validation/generation/diff checks;
- build;
- smoke tests;
- targeted E2E flows.

Do not run destructive production operations. Use safe local/test/dev environments and repository-provided test infrastructure.

For each core journey, validate the applicable matrix:
- happy path;
- invalid input;
- not found;
- conflict/concurrency issue;
- persistence or dependency failure;
- duplicate/retry behavior for retry-prone mutations;
- frontend loading/error/recovery state;
- persistence/result verification.

A core journey is not validated merely because the HTTP endpoint returns 2xx.

## 14. Required artifacts

When file tools are available, create/update the real implementation and these artifacts:

1. API implementation in the project architecture.
2. Real frontend API integration/client code.
3. OpenAPI document in the established repository location.
4. `docs/06-api-design.md`.
5. `project-state.json`.

Use `references/artifact-template.md` as the default structure. `docs/06-api-design.md` must contain at least:
- scope and baseline;
- source requirements and core journeys;
- architecture/protocol decision;
- requirement-to-API traceability matrix;
- endpoint/resource map;
- request/response conventions;
- error contract;
- pagination/filtering/sorting/search rules;
- idempotency and duplicate behavior;
- concurrency/precondition strategy where applicable;
- file transfer rules where applicable;
- external dependency/webhook behavior where applicable;
- versioning/backward-compatibility decision;
- OpenAPI synchronization strategy;
- backend integration notes;
- frontend integration notes;
- production mock audit;
- validation commands actually executed;
- baseline failures vs Stage 06 regressions;
- test/smoke/E2E evidence;
- unresolved risks/assumptions;
- Stage 07 handoff items.

## 15. Stage 07 boundary

Stage 07 owns final authentication and authorization design/hardening, including identity proofing, login/session/token lifecycle, permission enforcement, MFA, CSRF strategy where applicable, authentication abuse controls, and authorization policy completeness.

Stage 06 must still:
- preserve all existing auth controls;
- keep authorization hook points/context compatible with later enforcement;
- avoid exposing unauthenticated production shortcuts;
- document endpoints that require Stage 07 policy decisions;
- avoid hard-coding user identity or role assumptions into transport contracts.

Do not mark insecure temporary behavior as production-ready simply because Stage 07 follows.

## 16. Quality gate

Use the full gate in `references/testing-quality-gate.md`.

PASS requires all mandatory conditions below:
- Stage 05 predecessor verification succeeded;
- every core API-dependent requirement is traceably covered or explicitly blocked with a true external blocker;
- production frontend paths for integrated journeys call real backend operations;
- backend operations reach real persistence/external adapters where required;
- request/response/error contracts match implementation;
- OpenAPI is present and synchronized for HTTP APIs;
- production-reachable mock behavior for integrated journeys is eliminated;
- retry-prone commands have explicit duplicate/idempotency semantics;
- required validation checks were executed when the repository/tooling permits them;
- Stage 06 introduced no unresolved build/type/lint/test regression in the affected scope;
- representative core journeys are validated end-to-end when executable infrastructure exists;
- required documentation and state artifacts are updated;
- unresolved risks are acceptable for Stage 07 and do not invalidate API correctness/integration.

If a mandatory condition fails because of a correctable Stage 06 defect, repair it before finishing.

If a mandatory condition cannot be satisfied because of a true external blocker, mark the stage BLOCKED and record exact evidence and the minimum action needed to unblock it.

## 17. Project state update

Update `project-state.json` according to `references/project-state-contract.md`.

Preserve unknown keys and previous stage records. Record at minimum:
- stage id `06`;
- stage name `api-integration`;
- status;
- start/completion timestamp when available;
- artifacts changed/created;
- requirement coverage summary;
- material decisions;
- assumptions;
- risks;
- validation commands and outcomes;
- blocker details when blocked;
- next stage.

Write state only after the final quality-gate decision. Avoid leaving a false PASS if artifact writing or final validation fails.

## 18. Completion response

Provide a concise engineering handoff containing:
- what was implemented;
- important contract decisions;
- validation actually executed and outcomes;
- remaining risks or Stage 07 handoff items;
- blocker details if blocked.

Then end with exactly one of these marker pairs.

On success:
`STAGE_06_STATUS: PASS`
`NEXT_STAGE: 07-authentication-authorization`

On a true blocker:
`STAGE_06_STATUS: BLOCKED`
`NEXT_STAGE: NONE`
