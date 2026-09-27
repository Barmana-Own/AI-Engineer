# Test and Check Execution Policy

## Command discovery order

Discover authoritative commands from the project in this order:
1. CI workflows used by the repository;
2. package/task manifests (`package.json`, `pyproject.toml`, `Makefile`, `Taskfile`, `composer.json`, workspace files, etc.);
3. container/dev scripts;
4. current README/runbooks;
5. framework conventions only when no project command exists.

If sources disagree, inspect the command bodies and current CI. Record documentation drift as a finding.

## Before running a command

1. Read the script/target being invoked.
2. Identify side effects: DB reset, seed, deploy, file deletion, external service mutation.
3. Confirm working directory.
4. Confirm required services/environment variables.
5. Confirm the command does not target production.
6. Prefer locked/reproducible dependency installation.
7. Use `run_check.py` to capture evidence when possible.

## Typical test tiers

Not every repository has every tier. Determine applicability explicitly.

- formatter/check;
- lint/static analysis;
- typecheck/compile;
- unit tests;
- component tests;
- integration tests;
- contract/API tests;
- migration/schema tests;
- end-to-end/browser tests;
- security regression tests;
- smoke/health tests;
- production build/container tests.

## Zero-test and skipped-test policy

A command exiting 0 is not automatically a valid PASS.

Inspect output for:
- zero tests discovered unexpectedly;
- all tests skipped/disabled;
- filters selecting only a subset when full suite is required;
- snapshot updates masking regressions;
- coverage/config errors hidden as warnings;
- retries converting deterministic failures into apparent success.

Record suspicious behavior as a finding and rerun appropriately.

## Flaky test policy

Do not simply rerun until green.

When a required test is flaky:
1. reproduce at least enough to establish instability;
2. inspect whether flake indicates race, timing, external dependency, test isolation, or environment issue;
3. fix the root cause when feasible;
4. if it is truly environment-only and non-product, document evidence and stabilize the test harness;
5. do not mark PASS while a required test remains nondeterministically red.

## Dependency installation

Prefer the repository lockfile mechanism:
- npm: `npm ci` when appropriate;
- pnpm/yarn: frozen/immutable lock options when repository policy uses them;
- Python: project lock/environment mechanism when present;
- other ecosystems: equivalent locked restore.

Do not rewrite lockfiles just to make installation succeed unless the dependency repair itself is intentional and then re-run dependency/security/build/test gates.

## Test data

Use synthetic/test fixtures. Never require copying private production data into the review environment.

## Failure handling

A failed required command creates a finding and sets the related gate to FAIL. After repair, do not overwrite history conceptually: append new evidence and use the latest valid result for final verdict.
