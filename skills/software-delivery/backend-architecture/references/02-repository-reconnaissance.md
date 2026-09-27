# Repository Reconnaissance and Change Control

## Table of contents

1. Inspection sequence
2. Backend detection
3. Existing architecture assessment
4. Change strategy
5. Stack decision rules
6. Forbidden change patterns
7. Reconnaissance output

## 1. Inspection sequence

Inspect before editing. Prefer repository-aware search over assumptions.

Check:

- root directory layout;
- monorepo/workspace configuration;
- package/project manifests and lockfiles;
- runtime versions and toolchain files;
- application entry points;
- `src`, `app`, `server`, `api`, `backend`, `services`, `packages`, `libs`, and equivalent directories;
- tests and test configuration;
- CI workflows and required checks;
- Docker/Compose and local development files;
- `.env.example` or configuration documentation without exposing secrets;
- API schemas, generated clients, mocks, fixtures;
- existing DB clients, ORM config, migrations, and repository abstractions;
- logging, telemetry, queue/job, cache, storage, mail/SMS, payment, and other integration code;
- lint, formatting, typecheck, test, build, and dev scripts.

## 2. Backend detection

Determine the actual backend root from evidence such as:

- server entry point;
- route/controller registration;
- framework manifest;
- package scripts;
- workspace package role;
- import graph;
- deployment target.

Do not create `backend/` if the repository already uses `apps/api`, `server`, `src/server`, `services/api`, or another coherent location.

In a monorepo, identify shared packages and avoid copying types into the backend when a proper shared contract package already exists.

## 3. Existing architecture assessment

Classify existing backend components as:

- `KEEP`: consistent with Stage 04 boundaries;
- `ADAPT`: usable but needs a narrow boundary/refactor;
- `ISOLATE`: legacy or vendor-coupled code that should sit behind a port;
- `REPLACE_WITHIN_SCOPE`: unsafe or structurally blocking code whose replacement is necessary now;
- `DEFER`: issue belongs to a later stage and can be safely documented.

Assess at least:

- business logic inside controllers;
- direct ORM/database access from transport handlers;
- cyclic module dependencies;
- globally mutable state;
- vendor SDK types leaking into application/domain logic;
- duplicated validation/business rules;
- missing request context or authorization boundaries;
- hidden environment reads scattered through business code;
- sensitive logging;
- unbounded retries/timeouts;
- untestable hard-coded time/IDs only when they affect business behavior.

## 4. Change strategy

Use the smallest safe strategy:

### Extend

Choose when existing boundaries are healthy. Add missing modules/use cases/ports/tests in the same conventions.

### Refactor in place

Choose when behavior exists but transport, business, and persistence are entangled. Preserve behavior while extracting boundaries with tests.

### Strangler/isolation seam

Choose for a large legacy backend where a full rewrite is unjustified. Put new application/domain behavior behind clear interfaces and isolate legacy persistence/vendor code.

### Minimal scaffold

Choose only when no viable backend exists. Create the smallest production-oriented structure needed for Stage 04 and avoid speculative layers.

## 5. Stack decision rules

If a backend stack exists and is viable, keep it.

If no backend stack exists:

1. inspect repository language/tooling and Stage 03 ecosystem;
2. prefer a stable, actively supported runtime compatible with team/project constraints;
3. minimize new operational languages and package managers;
4. choose libraries with clear maintenance and security posture;
5. record the decision and alternatives in `docs/04-backend-architecture.md`.

Do not switch frameworks because another framework is more familiar to the agent.

## 6. Forbidden change patterns

Do not:

- create duplicate backend applications accidentally;
- replace the package manager or lockfile without necessity;
- perform repository-wide formatting unrelated to Stage 04;
- rename public APIs without upstream compatibility analysis;
- delete existing migrations/database code merely to satisfy the Stage 04 boundary;
- introduce a queue, event bus, cache, service mesh, CQRS, or microservices without a requirement-driven reason;
- add abstractions with only one speculative use and no testability/boundary benefit;
- hide build failures by disabling checks.

## 7. Reconnaissance output

Record in the architecture document:

- detected backend root and entry point;
- existing stack and versions when known;
- existing architecture summary;
- critical boundary violations found;
- change strategy selected;
- files/directories intentionally preserved;
- checks/commands discovered;
- risks that affect Stage 04.
