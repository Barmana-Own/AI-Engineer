# Stage 12 Execution Playbook

## Contents

- Phase 0: safe baseline
- Phase 1: Stage 11 precondition
- Phase 2: project discovery
- Phase 3: approved product intent
- Phase 4: requirement traceability
- Phases 5–9: repository, frontend, backend/API, data and security review
- Phases 10–12A: automated execution, clean-room runtime, operations and NFRs
- Phases 13–15: documentation, repair loop and release hygiene
- Phases 16–17: deterministic verdict, packaging and handoff

Use this as the authoritative sequence for the final review. Do not skip a phase because a prior stage claims it already passed.

## Phase 0 — Establish a safe baseline

1. Confirm the active project root. Avoid reviewing a parent folder that contains unrelated projects.
2. Capture repository state before mutation:
   - current branch/HEAD when Git exists;
   - `git status --short` or equivalent;
   - existing uncommitted/untracked user work;
   - runtime/toolchain versions available in the environment.
3. Do not clean, reset, checkout-overwrite, force-pull, or delete unknown user files.
4. Create `.final-review/` and initialize the review state.
5. Classify the environment:
   - local/development;
   - isolated test/ephemeral;
   - staging;
   - production or production-adjacent.
6. If production or production-adjacent, prohibit destructive setup/migration/seed/reset and write tests until explicit authorization and a safe plan exist.
7. Record assumptions needed to continue.

Exit criterion: workspace identity and mutation safety are known, and review state exists.

## Phase 1 — Prove the Stage 11 precondition

1. Read `project-state.json` if present.
2. Locate Stage 11 artifacts and explicit completion markers.
3. Confirm the evidence belongs to the same project/repository state.
4. Resolve state/artifact conflict using `project-state-contract.md`.
5. Set `G00`:
   - PASS only with trustworthy Stage 11 PASS evidence;
   - FAIL if Stage 11 failed, is contradictory, or cannot be distinguished from a stale artifact;
   - recover missing machine state only when an explicit trustworthy Stage 11 PASS artifact exists.

Exit criterion: `G00=PASS`; otherwise return to the owning stage.

## Phase 2 — Discover the actual project

1. Run `scripts/discover_project.py --root <project-root>`.
2. Inspect, do not merely trust, the generated project profile.
3. Identify:
   - package managers and lockfiles;
   - frontend applications;
   - backend services/workers;
   - database/ORM/migration systems;
   - API specifications;
   - container/orchestration files;
   - CI workflows;
   - test frameworks/directories;
   - task runners/Makefiles;
   - environment templates;
   - deployment/infra files;
   - documentation and previous stage artifacts.
4. Read authoritative scripts before executing them. For package manifests, inspect the actual command bodies for `build`, `test`, `lint`, `typecheck`, `migrate`, `seed`, `start`, `e2e`, `security`, and similarly named tasks.
5. Compare repository documentation to actual manifests. The repository is authoritative for what exists; documented commands must still be validated.
6. Record commands as discovered, not guessed.

Exit criterion: project topology and candidate commands are documented with enough confidence to plan the audit.

## Phase 3 — Reconstruct approved product intent

1. Read Stage 01 requirements and all approved scope-change artifacts.
2. Read later architecture/API/data/UI artifacts only to refine implementation intent, not to silently expand scope.
3. Enumerate:
   - actors/roles;
   - critical journeys;
   - business rules;
   - core functional requirements;
   - security/privacy requirements;
   - required integrations;
   - non-functional requirements that are release-blocking;
   - explicit exclusions/deferred items.
4. Resolve duplicate or renamed requirement identifiers while preserving traceability back to original IDs.
5. Never treat an unapproved feature found in code as an approved requirement.
6. Never treat an approved requirement as optional merely because code omitted it.

Exit criterion: a current approved requirement inventory exists.

## Phase 4 — Build traceability before deep testing

Create `.final-review/traceability.json` following `traceability-contract.md`.

For each core requirement map:
- implementation files/modules;
- routes/screens/endpoints/jobs involved;
- data entities/migrations when relevant;
- tests or verification evidence;
- current status;
- notes/known limitations.

Also identify:
- orphan code with no approved requirement;
- approved requirements with no implementation;
- implementation paths reachable only through mocks/dev bypasses;
- tests that no longer exercise the production implementation.

Set `G02` only after traceability is coherent.

Exit criterion: every core requirement has an explicit status and evidence path.

## Phase 5 — Repository and architecture integrity review

Inspect the source tree for:
- duplicate abandoned implementations;
- commented-out alternate production paths;
- unresolved merge conflict markers;
- release-relevant TODO/FIXME/HACK markers;
- generated junk committed accidentally;
- mock/fake adapters reachable in production;
- debug-only routes or flags;
- inconsistent environment handling;
- missing modules referenced by runtime code;
- circular or invalid dependency boundaries that break build/runtime;
- code/config drift across monorepo packages/services;
- stale feature flags that bypass approved behavior.

Confirm deployment/runtime topology matches the architecture actually implemented. Record discrepancies as findings, not merely notes.

Exit criterion: `G01` and architecture portions of `G03` have current evidence.

## Phase 6 — Frontend and user journey review

Follow `frontend-backend-api-review.md`.

At minimum:
1. enumerate production routes/screens for critical actors;
2. verify protected routes are actually protected;
3. verify empty/loading/error/success states on critical flows;
4. verify form validation and backend error rendering;
5. verify frontend production configuration targets the intended backend interface, not mock/local-only URLs;
6. verify session expiry/logout/unauthorized behavior;
7. verify sensitive/admin UI is not merely hidden client-side while backend remains permissive;
8. verify responsive/accessibility issues that make a core journey unusable;
9. verify asset/build references survive production build paths.

Exit criterion: critical journeys are reachable and coherent at the UI boundary, or blocking findings exist.

## Phase 7 — Backend, API and integration review

Follow `frontend-backend-api-review.md`.

At minimum:
1. map frontend requests to real backend routes/controllers;
2. compare request/response shapes with API docs/specs and client code;
3. verify input validation and deterministic error contracts;
4. verify business rules are enforced server-side where required;
5. verify authorization at the backend, not only UI;
6. verify idempotency/concurrency expectations for critical mutations where applicable;
7. verify integration adapters handle timeout/error/retry semantics safely;
8. verify background jobs/queues cannot silently drop critical work;
9. verify health/readiness endpoints represent actual dependency health appropriately;
10. sample representative success and negative paths with real runtime calls when possible.

Exit criterion: frontend/backend/API integration is internally consistent for critical journeys.

## Phase 8 — Database, migrations and persistence review

Follow `data-migrations.md`.

1. identify the canonical migration mechanism;
2. verify migration ordering and duplicate/conflicting migration IDs;
3. compare ORM/models/schema expectations with migrations;
4. verify indexes/constraints for critical uniqueness and ownership rules;
5. verify seed/bootstrap assumptions;
6. verify fresh database setup in local/test/ephemeral environment when possible;
7. verify application startup against the migrated schema;
8. where meaningful, verify upgrade from a representative prior schema state;
9. prohibit production reset/drop/truncate merely for this audit.

Exit criterion: `G07` and `G13` evidence satisfy persistence requirements or block release.

## Phase 9 — Authentication, authorization and security review

Follow `security-review.md` and `severity-and-findings.md`.

Re-test high-risk negative paths. Do not limit the review to static code reading when safe runtime verification is possible.

Mandatory focus:
- login/session/token lifecycle;
- logout/revocation expectations;
- password/reset/MFA flows when present;
- role/permission boundaries;
- object ownership/tenant isolation;
- admin/privileged operations;
- input injection classes relevant to the stack;
- file upload/download controls;
- CORS/CSRF/cookie/security headers as applicable;
- secrets/configuration;
- rate/abuse controls on sensitive endpoints;
- dependency vulnerabilities;
- debug/test bypasses;
- sensitive logging/error leakage.

Re-open previously closed security findings if current evidence contradicts them.

Exit criterion: no open blocking security finding and required security gates have evidence.

## Phase 10 — Execute code quality and automated test gates

Follow `test-execution.md`.

Execute discovered authoritative checks through `scripts/run_check.py` when possible. Typical order:
1. formatting check if repository defines one;
2. lint;
3. typecheck/compile-time analysis;
4. unit tests;
5. integration/contract tests;
6. API tests;
7. end-to-end tests;
8. security regression tests;
9. build/package checks.

Do not use `--force`, `--no-verify`, disabled-test flags, or broad test exclusions to manufacture a pass unless the repository's official CI uses them for a documented reason.

Exit criterion: all required runnable checks pass or a precise blocker is recorded.

## Phase 11 — Clean-room setup and runtime verification

Use the closest safe environment to a clean checkout/build:
1. install/restore dependencies using the repository's locked dependency mechanism;
2. provision required local/test services;
3. create a clean database when persistence exists;
4. apply migrations from zero;
5. load only safe deterministic seed data when required;
6. build production artifacts;
7. start the production-mode application/container when possible;
8. run health/readiness checks;
9. run representative critical smoke journeys;
10. stop temporary services cleanly without deleting unrelated resources.

If unavailable infrastructure prevents execution, classify each missed check under `NOT_RUN` and apply the gate matrix. Do not infer success from development-mode startup.

Exit criterion: clean setup and production-mode runtime are demonstrated to the extent required by the project.

## Phase 12 — Production and operations readiness

Follow `production-ops-readiness.md`.

Verify:
- documented environment variables and required secrets;
- sane production defaults;
- container/process entrypoints;
- health/readiness behavior;
- migrations/deployment order;
- rollback strategy;
- logging/metrics/tracing as appropriate;
- backup/restore expectations for stateful systems;
- scheduled/background worker operation;
- graceful shutdown and restart assumptions;
- known operational limits;
- incident/debug guidance that does not expose secrets.

Exit criterion: deployment is operationally understandable and does not rely on undocumented tribal knowledge for core startup/recovery.

## Phase 12A — Applicable non-functional requirements

Read `nonfunctional-review.md`. Evaluate only requirements that are approved, security-critical, or necessary for safe operation. Cover applicable performance/capacity, reliability/failure behavior, concurrency/consistency, accessibility, internationalization/RTL/timezones, privacy/data minimization and compatibility. Map release-relevant results back to G02, G03, G04, G05, G09 or G16 as appropriate.

Exit criterion: every approved blocking non-functional requirement has current evidence or a recorded blocker.

## Phase 13 — Documentation consistency

Verify README/runbooks against actual project commands and configuration.

At minimum document:
- supported runtime/toolchain versions;
- dependency installation;
- environment preparation;
- database migration/seed procedure;
- local development start;
- production build/start;
- test commands;
- major architecture/components;
- required external services;
- deployment order;
- known non-blocking issues;
- security-sensitive operational notes;
- exact artifact locations.

Documentation that contains stale commands is a defect.

Exit criterion: a competent new engineer can reproduce the supported setup without inventing missing core steps.

## Phase 14 — Repair loop

For every blocking defect, use `repair-loop.md`.

Important ordering:
1. record finding before modification;
2. identify owning stage and impacted gates;
3. patch smallest correct scope;
4. update/add regression test where meaningful;
5. update docs/spec/schema contracts;
6. record repair and changed files;
7. mark impacted gates stale/PENDING;
8. re-run impacted checks;
9. only then close the finding.

Repeat until no blocking defect remains or an external blocker prevents safe completion.

Exit criterion: no open blocking finding and no stale mandatory evidence.

## Phase 15 — Release hygiene and package preparation

1. Run `scan_release_hygiene.py`.
2. Review each High/Critical candidate manually; resolve false positives by a narrow allowlist entry with reason.
3. Remove/rewrite real secrets or private data from source/history-as-delivered, not merely from the final ZIP filter, when they are part of the release content.
4. Confirm release does not depend on `.env` secrets being bundled.
5. Confirm caches, logs, temp output, local DBs/dumps, VCS metadata and user-private files are excluded.
6. Re-run hygiene after any cleanup.

Exit criterion: no unsuppressed blocking hygiene finding.

## Phase 16 — Deterministic verdict and package finalization

Use a two-pass validation so the archive itself is evidence rather than an assumption.

1. Ensure G00–G18 have final statuses and no stale evidence.
2. Run `validate_final_gate.py --phase prepackage`. If it fails, repair; never hand-author PASS.
3. Generate the near-final `docs/12-final-review.md`, `project-state.json`, and a provisional `release-manifest.json`.
4. Build a preflight archive with `package_release.py`; inspect its member list and package result.
5. Resolve any package/hygiene defect, then set G19 PASS with preflight package evidence.
6. Run `validate_final_gate.py --phase final`.
7. Only after that PASS, update the report/project-state completion markers and rebuild `release-manifest.json` so their status is final. This content change makes the previous package evidence stale.
8. Rebuild the final archive. Confirm it contains the final report/manifest and excludes forbidden material. Record the new `.final-review/package-result.json`.
9. Re-affirm G19 with the final package evidence and run `validate_final_gate.py --phase final` once more. The validator output lives under `.final-review/` and therefore does not change the release archive.
10. Keep the archive SHA-256 in `.final-review/package-result.json` and the user-facing handoff. Do not embed the archive's own SHA-256 inside a manifest contained by that same archive; that would be self-referential.

Exit criterion: final artifacts and final archive are internally consistent with the evidence ledger and the last final validator verdict.

## Phase 17 — Handoff

For PASS, report:
- concise verdict;
- major checks actually executed;
- cross-stage repairs made;
- remaining non-blocking issues;
- artifact/package location;
- exact completion markers.

For FAIL, report:
- blocking findings;
- failed/essential NOT_RUN gates;
- earliest owning stage;
- repairs already attempted;
- exact failure markers.
