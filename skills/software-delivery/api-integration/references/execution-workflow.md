# Stage 06 Execution Workflow

## Contents
1. Purpose
2. Phase 0 - Establish execution context
3. Phase 1 - Verify predecessor and baseline
4. Phase 2 - Build requirement and journey inventory
5. Phase 3 - Build traceability matrix
6. Phase 4 - Decide API architecture and contract policy
7. Phase 5 - Design detailed contracts
8. Phase 6 - Design error and reliability behavior
9. Phase 7 - Establish OpenAPI authority and synchronization
10. Phase 8 - Implement backend transport integration
11. Phase 9 - Implement frontend integration
12. Phase 10 - Audit production mocks and fake paths
13. Phase 11 - Validate vertical slices
14. Phase 12 - Run repository-wide affected-scope checks
15. Phase 13 - Produce evidence and documentation
16. Phase 14 - Final gate and state transition
17. Blocking and recovery rules

## 1. Purpose

Use this workflow to make Stage 06 deterministic. Complete phases in order. A later phase may reveal a defect in an earlier phase; when that happens, return to the earliest affected phase, repair it, and re-run downstream checks.

Do not optimize for the appearance of completeness. Optimize for executable, traceable integration.

## 2. Phase 0 - Establish execution context

### Actions
1. Identify repository root.
2. Read repository-local instructions and contribution files.
3. Detect package manager(s), workspace layout, frontend app(s), backend app(s), shared packages, database layer, tests, and docs.
4. Locate `project-state.json` and Stage 01-05 artifacts.
5. Locate environment templates such as `.env.example`; never expose real secret values.
6. Record current branch and working-tree state when VCS tooling is available.
7. Identify user modifications that predate this stage.

### Output
Maintain a short internal repository map and add a summarized version to `docs/06-api-design.md`.

### Stop condition
Stop only if the project cannot be located or is unreadable.

## 3. Phase 1 - Verify predecessor and baseline

### Stage 05 verification
1. Read Stage 05 state using `project-state.json`.
2. Verify status equals `PASS`.
3. Verify referenced persistence artifacts exist or locate their current equivalent.
4. Confirm essential database/persistence code is callable by Stage 04 application logic.
5. If state claims PASS but artifacts are missing, treat this as a predecessor integrity defect and block Stage 06 unless the artifacts were clearly moved/renamed and can be resolved safely.

### Baseline validation
Identify and, when feasible, run the repository's existing relevant checks before Stage 06 edits. Examples:
- lint;
- typecheck;
- unit tests;
- backend compile/test;
- frontend build;
- integration tests.

Record failures as `baseline failures`. Do not falsely attribute them to Stage 06 later.

If baseline checks are too expensive or unavailable, record why and choose targeted alternatives.

## 4. Phase 2 - Build requirement and journey inventory

Read earlier-stage requirements, acceptance criteria, workflows, use cases, interfaces, schemas, and persistence notes.

For each core user journey, capture:
- actor;
- trigger;
- preconditions;
- user intent;
- expected state transition;
- data read/written;
- external side effect;
- success result;
- expected user-visible failure classes;
- requirement/acceptance IDs.

Classify each journey as:
- `read`;
- `mutation`;
- `upload/download`;
- `bulk`;
- `async/job`;
- `external callback/webhook`;
- `mixed`.

Identify flows that do not require an API and mark them `not-applicable` rather than inventing endpoints.

## 5. Phase 3 - Build traceability matrix

Create the traceability matrix before implementation.

For every API-dependent core requirement map:

`requirement -> frontend entry -> operation -> handler -> application use case -> persistence/external adapter -> response -> frontend state -> test evidence`

Rules:
- Never use a single vague row such as "CRUD API" for multiple materially different journeys.
- Split operations when validation, side effects, authorization context, idempotency, or response semantics differ materially.
- Mark missing links as `GAP` and resolve them before final gating unless truly blocked.
- Preserve requirement IDs exactly; do not renumber earlier-stage requirements.

## 6. Phase 4 - Decide API architecture and contract policy

Prefer existing architecture unless change is required.

Decide and document:
- REST/HTTP, GraphQL, RPC, or mixed protocol already used;
- public vs internal API surface;
- versioning strategy;
- naming convention;
- DTO ownership;
- schema authority;
- error envelope;
- pagination style;
- time/ID/money representation;
- OpenAPI authority model for HTTP APIs.

For a new REST surface, default to resource-oriented HTTP semantics. Use action endpoints only for domain commands that do not map cleanly to CRUD/resource transitions.

Do not introduce microservices, API gateways, event buses, GraphQL, or code generation solely because they are fashionable.

## 7. Phase 5 - Design detailed contracts

For each operation:
1. Define method and path/operation name.
2. Define path/query/header parameters.
3. Define request body schema.
4. Define validation constraints.
5. Define success status and response schema.
6. Define empty/no-content behavior.
7. Define not-found behavior.
8. Define conflict/concurrency behavior.
9. Define validation error behavior.
10. Define dependency failure behavior.
11. Define idempotency behavior for retry-prone mutations.
12. Define pagination/filter/sort/search semantics if list-like.
13. Define upload/download media and limits if file-based.
14. Define caching/precondition semantics if useful.
15. Define backward compatibility risk.

Check contract against actual domain and persistence constraints. Do not promise fields the backend cannot reliably produce.

## 8. Phase 6 - Design error and reliability behavior

Use `error-reliability-standards.md`.

Inventory failure classes from:
- transport validation;
- domain validation;
- missing entities;
- state conflicts;
- database constraints;
- optimistic concurrency;
- dependency timeout;
- dependency rejection;
- malformed dependency response;
- duplicate request;
- upload rejection;
- unexpected server error.

Map each class to stable client behavior and status/error code. Ensure frontend can distinguish user-correctable failures from transient/system failures.

For retries, explicitly decide whether the client, server, queue, or infrastructure owns retry behavior. Avoid stacked uncontrolled retries.

## 9. Phase 7 - Establish OpenAPI authority and synchronization

For HTTP APIs:
1. Locate existing OpenAPI tooling.
2. Choose `contract-first` or `code-first` based on repository convention.
3. Update/generate OpenAPI from the authoritative source.
4. Validate syntax and schema references.
5. Compare documented operations to implemented production routes.
6. Compare response/error/status semantics.
7. Record deviations as defects and fix them.

Never hand-edit generated OpenAPI if the repository clearly treats generated output as derived.

## 10. Phase 8 - Implement backend transport integration

Implement the smallest transport layer necessary to expose Stage 04 use cases through Stage 06 contracts.

For each route/handler:
- parse input once;
- validate at the intended boundary;
- map to an application command/query;
- call existing use-case/service logic;
- avoid direct database access from transport code when architecture separates layers;
- map application/domain result to DTO/status;
- normalize errors centrally when possible;
- preserve request/correlation context when present;
- add/adjust tests near the transport boundary.

Do not move business logic into controllers merely to satisfy frontend expectations. If application logic lacks required behavior, update the appropriate earlier-layer implementation minimally and record the reason.

## 11. Phase 9 - Implement frontend integration

Use `frontend-integration-standards.md`.

For each integrated journey:
1. Identify the UI event or data-loader entry point.
2. Replace production fixture/mock access with the real API integration layer.
3. Add/update typed DTOs or generated client types according to repository convention.
4. Map request data deliberately; do not pass entire UI state blindly.
5. Normalize response data before rendering when domain/UI shapes differ.
6. Implement loading state.
7. Implement empty state when applicable.
8. Map field validation errors to inputs when supported by the contract.
9. Implement conflict/dependency/system failure states.
10. Avoid stale response overwrites for rapidly changing queries/forms.
11. Confirm successful mutation updates or invalidates frontend state correctly.
12. Confirm refresh/reload reads persisted server truth rather than cached fake data.

## 12. Phase 10 - Audit production mocks and fake paths

Run static scan and manual inspection.

Look for:
- hard-coded arrays used as production data;
- feature flags that choose fake repositories in production;
- localStorage/sessionStorage acting as unintended source of truth;
- frontend service modules returning constants/promises without HTTP calls;
- in-memory backend repositories selected outside tests;
- sample API responses wired into production screens;
- environment defaults that silently select mock mode.

Do not remove legitimate test/development fixtures.

Classify findings:
- `production-reachable defect` - must repair;
- `test/dev isolated` - keep;
- `uncertain` - inspect build/runtime selection before deciding.

## 13. Phase 11 - Validate vertical slices

Validate a vertical slice per core journey.

A meaningful slice proves, where applicable:
`UI -> frontend client -> HTTP transport -> handler -> application logic -> persistence/external adapter -> response -> frontend state`

For mutations, also verify persisted state or subsequent readback.

For each core journey test applicable cases:
- success;
- invalid input;
- not found;
- state conflict;
- duplicate/retry;
- dependency/persistence failure;
- frontend recovery/retry behavior.

Use test infrastructure rather than destructive real-world actions. Do not trigger real payments, messages, production uploads, or irreversible external side effects unless explicitly authorized and safely sandboxed.

## 14. Phase 12 - Run repository-wide affected-scope checks

After targeted flows work, run the strongest feasible affected-scope checks.

Compare failures to the baseline:
- pre-existing unchanged failure -> document, do not falsely claim fixed;
- Stage 06-caused failure -> repair;
- ambiguous failure -> investigate enough to classify;
- environment-only failure -> document with evidence and alternate checks.

Do not use `--force`, ignore flags, test exclusion, or broad lint suppression to manufacture a green result.

## 15. Phase 13 - Produce evidence and documentation

Update `docs/06-api-design.md` with concrete repository paths and commands.

Evidence should include:
- implemented operations;
- traceability status;
- OpenAPI synchronization method;
- validation commands and exit outcomes;
- representative flow evidence;
- mock audit result;
- known baseline failures;
- unresolved risks;
- Stage 07 handoff.

Do not include secrets, bearer tokens, session cookies, private keys, passwords, or sensitive production payloads.

## 16. Phase 14 - Final gate and state transition

Run `testing-quality-gate.md` exactly.

If PASS:
1. Update Stage 06 state.
2. Set next stage to `07-authentication-authorization`.
3. Emit success markers.

If BLOCKED:
1. Record blocker category, evidence, impact, and minimum unblock action.
2. Do not add Stage 06 to completed PASS stages.
3. Set next stage to NONE.
4. Emit blocked markers.

## 17. Blocking and recovery rules

### Correctable implementation defect
Repair it in Stage 06 and re-run affected checks. Do not block simply because the first implementation failed.

### Missing non-critical detail
Choose a safe default, record it, continue.

### Missing critical external dependency
Block only the affected stage when it prevents a mandatory quality-gate condition.

### Pre-existing unrelated failure
Document it. If Stage 06 can still prove its own affected scope without masking the failure, it need not block the stage.

### Corrupt predecessor state
Block and identify the smallest predecessor repair needed. Do not fabricate predecessor PASS evidence.
