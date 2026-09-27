# Preflight and Test-Stack Discovery

## Purpose

Discover what the repository actually is before selecting test tools, commands, or architecture. Avoid framework duplication, unsafe execution, and false assumptions.

## Table of contents

1. Repository orientation
2. Stage 08 verification
3. Manifest and runtime discovery
4. Test framework discovery
5. CI command discovery
6. Service and dependency discovery
7. Environment safety classification
8. Existing-test health assessment
9. Discovery output
10. Decision rules

## 1. Repository orientation

Inspect the project root before editing anything.

Record:
- repository root;
- monorepo/workspace structure;
- application/service/package boundaries;
- runtime languages;
- frontend/backend/mobile/worker components;
- database(s);
- queues/caches/object storage/search services;
- infra/container files;
- source and test directory conventions;
- current git/worktree state when available.

Look for root-level and workspace-level manifests rather than assuming a single-package application.

Common evidence includes:
- `package.json`, `pnpm-workspace.yaml`, `yarn.lock`, `pnpm-lock.yaml`, `package-lock.json`;
- `pyproject.toml`, `requirements*.txt`, `poetry.lock`, `uv.lock`, `Pipfile`;
- `composer.json`;
- `pom.xml`, `build.gradle`, `build.gradle.kts`;
- `go.mod`;
- `Cargo.toml`;
- `.sln`, `.csproj`;
- `Dockerfile*`, `compose*.yml`, `docker-compose*.yml`;
- CI workflow files.

## 2. Stage 08 verification

Read `project-state.json` first when present.

Accept Stage 08 as passed only when an explicit Stage 08 record indicates `PASS`. Do not infer PASS solely because source code exists.

Then inspect Stage 08 artifacts for:
- fixed vulnerability IDs;
- security test cases;
- authorization matrix;
- accepted residual risks;
- new validation/sanitization rules;
- rate-limit behavior;
- token/session changes;
- upload/security controls;
- security-sensitive migrations.

Import these items into the Stage 09 risk matrix.

If Stage 08 state and artifacts conflict, record the conflict before proceeding.

## 3. Manifest and runtime discovery

Determine exact package/runtime choices from repository evidence.

Examples:
- Node.js version from `.nvmrc`, `.node-version`, `engines`, toolchain config, or CI;
- Python version from `pyproject.toml`, `.python-version`, Docker/CI;
- Java/JDK version from build config/CI;
- database version from Compose/Docker/CI;
- browser tooling version from lockfile and config.

Prefer the project's pinned version over the locally installed newest version.

## 4. Test framework discovery

Search for configuration, dependencies, scripts, imports, and file naming conventions.

### JavaScript/TypeScript

Look for:
- Vitest: `vitest.config.*`, `vitest` dependency/imports;
- Jest: `jest.config.*`, `jest` dependency/imports;
- Node test runner: `node:test` imports;
- Playwright: `playwright.config.*`, `@playwright/test`;
- Cypress: `cypress.config.*`, `cypress/`;
- Testing Library: `@testing-library/*`;
- Supertest or equivalent API helpers;
- MSW for external HTTP boundaries.

Inspect `package.json` scripts such as:
- `test`;
- `test:unit`;
- `test:integration`;
- `test:e2e`;
- `test:coverage`;
- `ci:test`;
- `check`.

### Python

Look for:
- `pytest.ini`;
- pytest config in `pyproject.toml`;
- `unittest` conventions;
- Django test config;
- FastAPI/Starlette test clients;
- coverage.py settings;
- tox/nox sessions.

### PHP

Look for PHPUnit/Pest config and Composer scripts.

### Java/Kotlin

Look for JUnit/TestNG/Mockito, Maven/Gradle test tasks, Spring test config, Testcontainers.

### Go

Look for `_test.go`, build tags, integration test folders, race-test CI commands.

### .NET

Look for xUnit/NUnit/MSTest packages, test projects, `dotnet test` CI commands.

### Rust

Look for module tests, `tests/`, feature-gated integration tests, cargo nextest if configured.

## 5. CI command discovery

CI is often the best source of canonical commands.

Inspect workflows/pipelines for:
- install command;
- build/typecheck/lint prerequisites;
- test command;
- service containers;
- environment variables;
- DB migration/setup steps;
- browsers installed;
- coverage collection;
- parallel/sharded execution;
- cache behavior.

Prefer reproducing the CI-equivalent command locally when safe and practical.

Do not invent a canonical command when CI or project scripts already define one.

## 6. Service and dependency discovery

Build a dependency inventory for tests:

| Dependency | Needed by | Safe test strategy |
|---|---|---|
| SQL database | repositories/migrations | disposable DB/container/schema |
| Redis/cache | session/cache/locks | local container or isolated DB index |
| Queue | async jobs | test broker or in-memory adapter only when contract remains tested |
| Object storage | uploads/files | MinIO/local emulator/temp filesystem depending adapter contract |
| Email/SMS | notifications | fake provider/outbox capture |
| Payment | billing | provider sandbox or boundary mock |
| Third-party API | integration | contract fixture/mock server unless sandbox is required |

Identify which boundaries need real integration and which must be simulated for safety/reliability.

## 7. Environment safety classification

Classify the active target:
- `LOCAL_EPHEMERAL`
- `LOCAL_PERSISTENT_TEST`
- `CI_EPHEMERAL`
- `REMOTE_TEST_SANDBOX`
- `SHARED_STAGING`
- `PRODUCTION_OR_UNSAFE`
- `UNKNOWN`

Never run destructive tests against `PRODUCTION_OR_UNSAFE` or `UNKNOWN`.

Treat an environment as suspicious when:
- DB host/domain is a production hostname;
- credentials belong to real customer/user services;
- base URL resolves to public production;
- environment name says `prod`, `production`, or equivalent;
- destructive cleanup would affect shared data;
- external side effects can charge money or message real users.

If uncertain, prefer non-destructive discovery and mark execution blocked until safety can be proven from project configuration.

## 8. Existing-test health assessment

Before adding tests, establish baseline health.

When safe and reasonably fast:
1. run the smallest existing test command;
2. record existing failures;
3. distinguish pre-existing failures from new changes;
4. inspect skipped/quarantined tests;
5. inspect known flaky retries;
6. inspect coverage exclusions;
7. inspect test-only TODO/FIXME markers that affect critical areas.

Do not attribute pre-existing failures to Stage 09 changes without evidence.

## 9. Discovery output

Write `docs/09-test-stack.json` when the helper script is available.

The inventory should include:
- detected ecosystems;
- manifests/lockfiles;
- frameworks;
- test config files;
- candidate commands;
- CI files;
- databases/migrations;
- E2E tooling;
- uncertainty notes.

Verify generated inventory manually against the repository before using it.

## 10. Decision rules

Use these rules consistently:

1. Existing compatible framework wins over introducing a new one.
2. Existing project scripts win over handwritten raw commands.
3. CI-equivalent command wins as the definition of full-suite execution.
4. Lockfile/pinned runtime wins over latest-version assumptions.
5. Repository convention wins over personal style preference.
6. Safe isolated test infrastructure wins over shared persistent infrastructure.
7. Real internal boundary wins over mocking the layer under test.
8. External provider sandbox/mock wins over real production side effects.
9. Missing critical infrastructure becomes an explicit blocker or test-infra task, never a silent skip.
10. Discovery evidence must be recorded before material framework changes.
