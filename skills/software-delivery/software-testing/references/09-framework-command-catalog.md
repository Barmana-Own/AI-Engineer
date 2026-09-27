# Framework and Command Discovery Catalog

## Purpose

Provide command heuristics for discovery. Use project-defined scripts/config/CI as the source of truth. Never execute a catalog command merely because the ecosystem was detected.

## Table of contents

1. JavaScript / TypeScript
2. Python
3. PHP
4. Java / Kotlin
5. Go
6. .NET
7. Rust
8. Database/migration tools
9. Browser/E2E tools
10. Coverage
11. Command safety checks

## JavaScript / TypeScript

### Package manager selection

Prefer lockfile evidence:
- `pnpm-lock.yaml` → `pnpm`;
- `yarn.lock` → `yarn`;
- `package-lock.json` → `npm`;
- Bun lockfile/config → `bun` when project intentionally uses Bun.

Use root/workspace scripts before direct runner invocation.

Common candidates:
- `npm test` / `pnpm test` / `yarn test`;
- `npm run test:unit`;
- `npm run test:integration`;
- `npm run test:e2e`;
- `npm run test:coverage`;
- `npx vitest run` only when project has Vitest and no preferred script;
- `npx jest --runInBand` only when project conventions justify it;
- `npx playwright test` when configured;
- `npx cypress run` when configured.

For monorepos, respect workspace filters/turbo/nx commands already defined.

## Python

Inspect environment manager first.

Common candidates:
- `pytest`;
- `python -m pytest`;
- `pytest tests/unit`;
- `coverage run -m pytest`;
- `tox`;
- `nox`;
- framework-specific commands such as Django's test runner when the project uses it.

Do not create a second virtual environment convention if the project already uses Poetry/uv/pipenv/tox/nox.

## PHP

Common candidates:
- `composer test`;
- `vendor/bin/phpunit`;
- `vendor/bin/pest`.

Prefer Composer scripts when present.

## Java / Kotlin

Common candidates:
- `./mvnw test`;
- `./mvnw verify`;
- `./gradlew test`;
- project-specific integrationTest tasks.

Prefer repository wrappers (`mvnw`, `gradlew`) over globally installed tools.

## Go

Common candidates:
- `go test ./...`;
- `go test -race ./...` when race testing is part of project/CI expectations;
- tagged integration commands defined by project scripts/CI.

Do not add `-race` blindly when environment/platform cannot support it; document applicability.

## .NET

Common candidates:
- `dotnet test`;
- solution/project-specific test commands;
- coverage collector commands already configured.

## Rust

Common candidates:
- `cargo test`;
- `cargo nextest run` only when project uses nextest;
- feature-specific commands defined in CI.

## Database/migration tools

Discover from project code/config. Examples include:
- Prisma;
- Drizzle;
- Knex;
- Sequelize;
- TypeORM;
- Alembic;
- Django migrations;
- Rails migrations;
- Flyway/Liquibase;
- EF Core;
- Laravel migrations.

Never run migration/reset commands until the target database is proven safe/test-only.

## Browser/E2E tools

### Playwright

Look for:
- `playwright.config.*`;
- webServer config;
- projects/browser matrix;
- storageState/auth setup;
- CI install steps.

Use project scripts first.

### Cypress

Look for:
- `cypress.config.*`;
- component vs e2e setup;
- baseUrl/server start command;
- CI recording settings.

Do not send results to external recording services unless project configuration/credentials intentionally do so and it is safe.

## Coverage

Use the project's existing coverage provider.

Do not install a new coverage stack only to report a percentage unless the project lacks any way to identify important gaps and the addition is low-risk.

## Command safety checks

Before executing a discovered command, answer:
1. What directory must it run in?
2. What environment/config does it load?
3. Which services/databases does it touch?
4. Can it mutate shared/production data?
5. Does it send external messages/payments/webhooks?
6. Does it require destructive DB reset?
7. Does it require credentials unavailable in the current environment?

If safety is uncertain, inspect configuration first.
