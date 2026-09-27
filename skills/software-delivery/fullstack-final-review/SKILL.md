---
name: fullstack-final-review
description: "Stage 12 and final independent release gate for an autonomous full-stack delivery workflow. Use after Stage 11 has verifiably passed to re-audit the actual repository from first principles, reconstruct approved requirements, establish requirement-to-code/test traceability, verify frontend/backend/API/database/auth/security integration, execute discovered quality/build/test/migration/runtime checks, repair release-blocking defects, re-run invalidated gates, verify production and operations readiness, generate evidence-backed release artifacts, and package only a release that satisfies deterministic blocking criteria. Never trust earlier PASS claims without current evidence."
---

# Stage 12 — Full-Stack Final Review

## Mission

Operate as the independent release authority for the project. Treat earlier stages as inputs, not proof. Inspect the current source tree, reproduce the intended product from approved artifacts, execute verifications against the real implementation, repair defects within scope, and refuse completion until every blocking release condition is satisfied or explicitly proven impossible because of an external dependency.

A polished report is not completion. Completion requires a reproducible evidence trail and a deterministic final verdict.

## Non-negotiable operating rules

1. **Never trust inherited PASS markers blindly.** Re-verify material claims against the current repository and current executable state.
2. **Never claim a command, test, migration, build, smoke check, security check, or runtime verification ran unless it actually ran.** Use `NOT_RUN` with a precise reason when execution is unavailable.
3. **Never convert missing evidence into PASS.** Unknown is not success.
4. **Never perform destructive or production-mutating operations without explicit user authorization.** Do not reset/drop/truncate production data, run destructive migrations on production, deploy to production, rotate credentials, modify live customer data, or invoke destructive external actions merely to satisfy this gate.
5. **Prefer isolated verification environments.** Use local/test/ephemeral databases and services for destructive setup, migration, seed, reset, and end-to-end tests.
6. **Preserve user work.** Record repository baseline before changes. Never use destructive Git recovery commands against user changes. Do not overwrite unrelated modifications.
7. **Repair instead of merely reporting when the defect is safely repairable in the active project.** Make the smallest coherent change, update tests/docs/contracts that the change invalidates, then re-run every affected gate.
8. **Invalidate stale evidence.** Any code/config/schema/dependency change makes relevant prior evidence stale. Re-running the affected checks is mandatory before PASS.
9. **Prefer repository-defined commands.** Discover commands from manifests, CI, Makefiles, task runners, container files, and documentation. Do not invent commands when an authoritative project command exists.
10. **Treat external/time-sensitive facts as external facts.** Use current authoritative documentation when behavior depends on current framework/API/security/deployment rules.
11. **Separate verified facts, assumptions, findings, repairs, and unverified items.** Do not blur them in prose.
12. **Stop only for true external blockers.** Non-critical ambiguity should be resolved by the safest reasonable engineering assumption and recorded.

## Required working files

When file/code tools are available, maintain the following during the review:

- `.final-review/project-profile.json` — discovered stack, commands, topology, CI and runtime signals.
- `.final-review/review-state.json` — gate states, findings, repairs, invalidations, assumptions, blockers.
- `.final-review/evidence.json` — command and verification evidence ledger.
- `.final-review/logs/` — captured command output created by the runner.
- `.final-review/traceability.json` — requirement-to-implementation/test/evidence mapping.
- `.final-review/hygiene-report.json` — secret/release-hygiene scan results.
- `docs/12-final-review.md` — human-readable release audit.
- `release-manifest.json` — machine-readable final release manifest.
- `project-state.json` — orchestration state, preserving unknown keys.

The `.final-review/` directory is audit working state. It is normally excluded from the distributable project archive unless the user explicitly asks to include audit evidence.

## Mandatory execution sequence

Follow `references/execution-playbook.md` exactly. In summary:

1. establish a non-destructive baseline and Stage 11 precondition;
2. discover the project and authoritative commands;
3. reconstruct approved product scope and critical journeys;
4. build requirement traceability;
5. inspect repository, architecture, frontend, backend, API, database, auth and integration consistency;
6. perform security and release-hygiene review;
7. execute static checks and automated tests;
8. verify clean setup/migrations in a safe environment;
9. verify production build/runtime/container and representative smoke flows when possible;
10. verify observability, deployment/rollback/runbooks and documentation;
11. repair defects and invalidate/re-run affected evidence;
12. compute the deterministic release verdict;
13. write final artifacts and package the project only after the release gate passes.

Do not reorder phases merely to obtain a green result. Earlier discovery can change which later checks are required.

## Deterministic tooling

Use the bundled scripts when code execution is available:

- `scripts/discover_project.py` — inspect repository manifests/topology and create `project-profile.json`.
- `scripts/review_state.py` — initialize/update gates, findings, repairs, assumptions and invalidations.
- `scripts/run_check.py` — execute a real command without a shell, capture output, and append evidence.
- `scripts/scan_release_hygiene.py` — scan for tracked secrets, sensitive artifacts, bypasses and release-hygiene hazards.
- `scripts/validate_final_gate.py` — compute whether Stage 12 may PASS from review state, traceability and hygiene evidence.
- `scripts/build_release_manifest.py` — create `release-manifest.json` from verified state.
- `scripts/package_release.py` — build a filtered project archive after blocking hygiene findings are resolved or explicitly allowlisted with justification.

Use `python3` unless the environment establishes another Python executable. If Python cannot run, follow the same contracts manually and record the limitation.

## Reference contracts

Read the relevant reference before executing that domain:

- `references/execution-playbook.md` — authoritative end-to-end review procedure and phase exit criteria.
- `references/gate-matrix.md` — required gate IDs, blocking rules, required evidence and `NOT_RUN` policy.
- `references/evidence-contract.md` — evidence quality, freshness, command capture and stale-evidence rules.
- `references/traceability-contract.md` — requirement coverage and orphan/dead-path detection.
- `references/severity-and-findings.md` — severity taxonomy, P0/P1 mapping and blocking policy.
- `references/frontend-backend-api-review.md` — UI, API, backend and cross-layer integration review.
- `references/security-review.md` — authn/authz, tenant/ownership, injection, uploads, secrets, dependencies and negative-path review.
- `references/data-migrations.md` — schema/migration/seed/data-safety verification.
- `references/test-execution.md` — command discovery, test tiers, clean-room execution and flake policy.
- `references/production-ops-readiness.md` — configuration, containers, health, observability, deployment, rollback and runbooks.
- `references/nonfunctional-review.md` — performance, reliability, concurrency, accessibility, i18n, privacy and compatibility checks when applicable.
- `references/repair-loop.md` — ownership, smallest-correct-fix, invalidation and regression protocol.
- `references/packaging-policy.md` — package allow/deny rules and sensitive-file handling.
- `references/project-state-contract.md` — Stage 11 proof, Stage 12 state update and conflict handling.
- `references/output-contracts.md` — exact final report and manifest content.
- `references/traceability.schema.json`, `references/review-state.schema.json`, and `references/release-manifest.schema.json` — machine-readable structural contracts.
- `references/hygiene-allowlist.example.json` — narrow false-positive disposition example; never use it to suppress real secrets.

## Stage 11 precondition

Before substantive review, prove Stage 11 PASS using `references/project-state-contract.md`.

- A Stage 11 prose summary alone is insufficient when it contradicts machine-readable state or the current source tree.
- If machine-readable state is missing but a trustworthy Stage 11 artifact contains an explicit PASS marker and matches the active project, reconstruct the missing state and document the recovery.
- If Stage 11 status is contradictory, ambiguous, or demonstrably stale, set Gate `G00` to `FAIL` and return to the owning stage instead of inventing PASS.

## Gate handling

Initialize all gates from `references/gate-matrix.md` with status `PENDING`. Each gate must end in exactly one of:

- `PASS` — required evidence exists and is current.
- `FAIL` — a blocking criterion is violated or an attempted required check failed.
- `NOT_RUN` — execution was impossible; reason and release impact are recorded.

`NOT_RUN` is never a soft synonym for PASS. Essential gates marked as non-waivable in the gate matrix block production-ready status when `NOT_RUN`.

## Repair behavior

For every defect:

1. create a finding with severity, confidence, affected requirement/journey, owning stage, evidence and blocking status;
2. identify root cause, not only the visible symptom;
3. make the smallest coherent fix that preserves approved behavior;
4. add or update regression coverage where technically meaningful;
5. update API/schema/docs/contracts affected by the repair;
6. record the repair and changed files;
7. invalidate all gates whose evidence is now stale;
8. re-run invalidated gates and dependent smoke flows;
9. close the finding only after current evidence proves the fix.

Do not suppress a finding merely to make the release pass. An allowlist is acceptable only for a demonstrated false positive or an explicitly accepted non-blocking risk, with reason and scope.

## Release decision

Run `scripts/validate_final_gate.py` when possible. Stage 12 may PASS only when all of the following are true:

- Stage 11 precondition is proven;
- every approved core requirement is implemented or explicitly excluded by approved scope;
- no core requirement is `MISSING`, `BROKEN`, or lacks required implementation evidence;
- all mandatory gates satisfy the gate matrix;
- required builds and runnable test suites pass;
- clean setup/migration is proven in a safe executable environment when the project contains persistence;
- frontend/backend/API/database/auth flows are coherent for critical journeys;
- no open P0/P1 or Critical/High security finding remains;
- no unresolved intentional auth/security/test bypass exists;
- no real secret or production-private data is intended for the release artifact;
- production configuration and operational procedures are coherent for the stated deployment model;
- every repair has current regression evidence;
- the report distinguishes `PASS`, `FAIL`, and `NOT_RUN` truthfully.

A non-critical `NOT_RUN` may remain only when the gate matrix permits it and the reason is documented. If an essential verification cannot run, the final verdict is not production-ready.

## Required final artifacts

Create/update the artifacts defined in `references/output-contracts.md`. At minimum:

- `docs/12-final-review.md`
- `release-manifest.json`
- `project-state.json`
- `README.md` when missing or materially incomplete
- final distributable archive when supported and the gate passes

Never place real `.env` files, keys, tokens, customer data, database dumps, dependency caches, VCS internals, or audit logs containing secrets into the release archive.

## Completion markers

On successful final gate, end the user-facing completion response with exactly:

`STAGE_12_STATUS: PASS`
`WORKFLOW_STATUS: COMPLETE`
`NEXT_STAGE: NONE`

If the release gate fails, end with exactly:

`STAGE_12_STATUS: FAIL`
`WORKFLOW_STATUS: REPAIR_REQUIRED`
`NEXT_STAGE: <owning-stage-id>`

Choose the owning stage from the earliest material stage responsible for the blocking defect. If multiple stages own blockers, choose the earliest blocking owner and list the others in the report.
