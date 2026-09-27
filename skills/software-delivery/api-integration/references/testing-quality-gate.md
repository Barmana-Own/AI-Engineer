# Stage 06 Testing and Quality Gate

## Contents
1. Testing philosophy
2. Baseline vs regression
3. Contract validation
4. Backend integration tests
5. Frontend integration tests
6. End-to-end vertical slices
7. Mock audit
8. Required evidence table
9. Mandatory gate
10. Blocker classification
11. PASS/BLOCKED procedure

## 1. Testing philosophy

Test enough to prove contract correctness and real integration, not merely isolated function behavior.

Prefer the repository's existing test stack. Add targeted tests where Stage 06 introduces contract or integration behavior that lacks coverage.

Do not remove tests, weaken assertions, disable type safety, silence lint broadly, or skip failing suites merely to achieve PASS.

## 2. Baseline vs regression

Before edits, capture relevant existing failures when feasible.

At final validation classify every failure as:
- `pre-existing`;
- `Stage 06 regression`;
- `environment/infrastructure limitation`;
- `unknown` requiring investigation.

All Stage 06 regressions in affected scope must be fixed before PASS.

A documented pre-existing unrelated failure does not automatically block Stage 06 if Stage 06 quality can still be demonstrated without hiding it.

## 3. Contract validation

For HTTP APIs verify:
- OpenAPI parses/validates using repository tooling when available;
- every Stage 06 production route is documented or intentionally excluded with rationale;
- method/path/status/request/response/error semantics match implementation;
- generated clients/types are regenerated when codegen is part of the project;
- contract diff does not introduce accidental breaking changes to already-consumed APIs.

If automated contract validation is absent, manually inspect representative operations and record the limitation. For a mature/public API, absence of meaningful contract validation is a risk that may require adding tooling.

## 4. Backend integration tests

For each core operation cover applicable cases:
- valid request -> expected status/response;
- invalid request -> stable validation error;
- missing entity -> expected not-found behavior;
- domain/state conflict -> expected conflict code;
- persistence constraint/failure mapping;
- external dependency failure mapping;
- duplicate/idempotency behavior;
- optimistic concurrency behavior when used;
- file size/type rejection when file operation exists.

Verify side effects/persistence, not only response status.

## 5. Frontend integration tests

Cover applicable behavior:
- client constructs correct request;
- server success maps to expected state;
- server validation maps to form fields;
- not-found/conflict maps to intended UX;
- transient dependency/system failure shows recoverable state;
- successful mutation invalidates/updates data correctly;
- failed optimistic mutation rolls back;
- stale/cancelled queries do not overwrite newer state;
- production UI path is not backed by fixture data.

## 6. End-to-end vertical slices

At least one representative vertical slice must be validated for each materially distinct core journey class when executable infrastructure exists.

Examples of materially distinct classes:
- read/list/detail;
- create mutation;
- update/state transition;
- file upload/download;
- bulk operation;
- external callback/webhook;
- asynchronous job.

A vertical slice should prove the relevant path from frontend to persisted/external effect and back.

For destructive/high-impact integrations use sandbox/test doubles at the external boundary while keeping the internal production path real.

## 7. Mock audit

Run `scripts/scan_production_mocks.py` and manually inspect candidates.

PASS requires no known production-reachable fixture/fake path for a journey claimed as integrated.

The scanner is heuristic. A clean scan is not proof by itself, and a hit is not automatically a defect.

## 8. Required evidence table

Record an evidence table in `docs/06-api-design.md` with columns:
- check/flow;
- command or inspection method;
- scope;
- result;
- evidence summary;
- classification (`pass`, `pre-existing`, `blocked`, `not-applicable`).

Do not include secrets in command output excerpts.

## 9. Mandatory gate

Stage 06 PASS requires every mandatory item below.

### A. Predecessor integrity
- Stage 05 is verified PASS.
- required persistence/application artifacts exist.

### B. Coverage and traceability
- every core API-dependent requirement has a complete traceability row;
- no unexplained `GAP` remains for core scope.

### C. Contract quality
- operation semantics are defined;
- request/response/error schemas are consistent;
- list operations are bounded;
- retry-prone mutations have duplicate/idempotency semantics;
- concurrency behavior is defined where lost updates matter;
- file contracts are bounded and indirect where applicable.

### D. Implementation integrity
- backend transport calls intended application/domain logic;
- backend reaches real persistence/external adapter;
- frontend production path calls real backend;
- production-reachable mock paths are removed for integrated journeys.

### E. OpenAPI integrity
For HTTP APIs:
- OpenAPI exists;
- authority model is recorded;
- operations and schemas are synchronized with implementation;
- available validation/codegen checks pass or limitations are documented and manually mitigated.

### F. Validation integrity
- relevant lint/typecheck/build checks pass in affected scope or only documented unrelated pre-existing failures remain;
- targeted contract/integration tests pass;
- representative vertical slices pass when infrastructure permits execution;
- Stage 06 regressions are zero at completion.

### G. Performance and operability sanity
- core growing-data paths are bounded;
- no known obvious N+1/unbounded-query defect remains in core integrated flows;
- dependency timeouts/fan-out are bounded where relevant;
- existing observability middleware/conventions are preserved;
- no new sensitive logging is introduced.

### H. Artifact integrity
- `docs/06-api-design.md` is complete;
- `project-state.json` is valid and preserves prior state;
- Stage 07 handoff items are explicit.

## 10. Blocker classification

A blocker is valid only when it prevents a mandatory gate and cannot be safely repaired within Stage 06.

Valid examples:
- required private upstream API contract unavailable;
- required sandbox credential unavailable for the only meaningful validation path;
- Stage 05 PASS state is missing/corrupt and required persistence layer does not exist;
- mandatory business semantics conflict and repository evidence cannot resolve them;
- inaccessible mandatory infrastructure prevents proving a hard acceptance criterion and no safe local/test substitute exists.

Usually not blockers:
- choosing endpoint names;
- choosing a standard pagination default;
- minor UI wording;
- a fixable failing test;
- missing docs that Stage 06 can create;
- obvious type errors introduced during implementation.

## 11. PASS/BLOCKED procedure

### PASS
1. Confirm all mandatory gate sections A-H.
2. Run `scripts/validate_stage06_artifacts.py` if compatible with repository layout.
3. Update state to PASS.
4. Record next stage as `07-authentication-authorization`.
5. Emit PASS markers.

### BLOCKED
1. Identify the exact mandatory item that cannot pass.
2. Record evidence, impact, and minimum unblock action.
3. Keep stage status BLOCKED; do not list it as completed PASS.
4. Record next stage NONE.
5. Emit BLOCKED markers.
