# Evidence Artifacts and Final Quality Gate

## Purpose

Make Stage 09 output auditable by humans and machine-readable by the orchestrator. Define exact artifact structure and PASS/BLOCKED rules.

## Table of contents

1. Required artifacts
2. `docs/09-test-plan.md`
3. `docs/09-test-results.md`
4. `docs/09-test-summary.json`
5. `project-state.json`
6. Status vocabulary
7. Final gate checklist
8. Critical NOT_RUN policy
9. Evidence consistency rules
10. Final response format

## 1. Required artifacts

Create/update:
- actual automated tests in repository-standard locations;
- `docs/09-test-stack.json` when discovery helper can run;
- `docs/09-test-plan.md`;
- `docs/09-test-results.md`;
- `docs/09-test-summary.json`;
- `project-state.json`.

Do not create empty placeholder files merely to satisfy artifact checks.

## 2. `docs/09-test-plan.md`

Use this structure:

```markdown
# Stage 09 Test Plan

## Context and Inputs
## Stage 08 Security Regression Inputs
## Repository/Test Stack
## Test Environment and Safety
## Risk Model
## Requirement and Risk Traceability
## Suite Plan
## Data and Migration Plan
## Security Regression Plan
## Frontend/E2E Plan
## Execution Order
## Exit Criteria
## Assumptions and Limitations
```

### Requirement/risk traceability table

Include at least:

| Source ID | Priority | Requirement/Risk | Failure Impact | Test Layer | Test IDs | Positive | Negative | Boundary | Recovery | Planned Status |
|---|---|---|---|---|---|---|---|---|---|---|

### Suite plan table

Include:

| Suite ID | Type | Scope | Command | Criticality | Dependencies | Expected evidence |
|---|---|---|---|---|---|---|

Use `P0`, `P1`, `P2`, `P3` consistently.

## 3. `docs/09-test-results.md`

Use this structure:

```markdown
# Stage 09 Test Results

## Executive Verdict
## Environment
## Commands Executed
## Suite Results
## Requirement and Risk Coverage
## Security Regression Results
## Data/Migration/Concurrency Results
## Frontend/E2E Results
## Flakiness Verification
## Defects Found and Fixed
## Unresolved Failures and Blockers
## NOT_RUN / NOT_APPLICABLE Items
## Coverage Metrics
## Quality Gate Evaluation
## Final Verdict
```

### Commands table

Include:

| Command ID | Command | Working Directory | Purpose | Exit Code | Passed | Failed | Skipped | Duration | Evidence |
|---|---|---|---|---:|---:|---:|---:|---|---|

Use `unknown` rather than inventing counts the runner did not report.

### Suite results table

Include:

| Suite ID | Type | Priority Scope | Status | Passed | Failed | Skipped | Command ID | Notes |
|---|---|---|---|---:|---:|---:|---|---|

### Defect table

Include:

| Defect ID | Classification | Priority | Requirement/Risk | Reproduction Test | Root Cause | Fix | Verification |
|---|---|---|---|---|---|---|---|

Do not list a defect as fixed without a passing regression test or equivalent automated evidence.

## 4. `docs/09-test-summary.json`

Create valid JSON with this minimum schema:

```json
{
  "stage": "09",
  "status": "PASS",
  "environment_classification": "LOCAL_EPHEMERAL",
  "stage08_verified": true,
  "commands": [
    {
      "id": "CMD-001",
      "command": "npm test",
      "exit_code": 0,
      "status": "PASS"
    }
  ],
  "suites": [
    {
      "id": "SUITE-UNIT",
      "type": "unit",
      "criticality": "P1",
      "status": "PASS",
      "passed": 42,
      "failed": 0,
      "skipped": 0,
      "not_run_reason": null
    }
  ],
  "risk_coverage": {
    "p0_total": 3,
    "p0_covered": 3,
    "p1_total": 8,
    "p1_covered": 8
  },
  "authz_negative_paths": {
    "required": true,
    "passed": 12,
    "failed": 0,
    "not_run": 0
  },
  "security_regressions": {
    "required": true,
    "passed": 5,
    "failed": 0,
    "not_run": 0
  },
  "unresolved_failures": [],
  "unresolved_flaky_tests": [],
  "critical_not_run": [],
  "defects_fixed": ["DEF-09-001"],
  "artifacts": [
    "docs/09-test-plan.md",
    "docs/09-test-results.md",
    "docs/09-test-summary.json"
  ],
  "next_stage": "10-qa-debugging"
}
```

Additional keys are allowed. Preserve useful project-specific evidence.

### Status rules

Allowed top-level `status`:
- `PASS`;
- `FAIL`;
- `BLOCKED`.

Allowed suite `status`:
- `PASS`;
- `FAIL`;
- `BLOCKED`;
- `NOT_RUN`;
- `NOT_APPLICABLE`.

Do not use `PASS_WITH_WARNINGS` to bypass the gate. Put non-blocking notes in dedicated fields.

## 5. `project-state.json`

Preserve unknown existing keys.

Add/update Stage 09 under `completed_stages` using the project's established structure. Include at least:
- stage ID/name;
- status;
- artifacts;
- executed command summary;
- material decisions;
- assumptions;
- unresolved risks/blockers;
- defects fixed;
- next stage.

If the project's `completed_stages` is a map, prefer key `09` or its established naming convention. If it is a list, append/update the Stage 09 record without duplicating it.

Do not rewrite unrelated stage records.

## 6. Status vocabulary

Use statuses precisely.

### PASS

The suite/Stage ran and met its required assertions/gate.

### FAIL

The suite ran and produced a valid unresolved failure, or the Stage quality gate is not met while work is technically executable.

### BLOCKED

Execution/verification cannot proceed credibly due to critical unavailable external dependency, unsafe environment, unresolved specification conflict, or another blocker that cannot be repaired within Stage 09.

### NOT_RUN

The suite was applicable but not executed. Always give a reason and criticality.

### NOT_APPLICABLE

The suite/category does not apply to this project. Explain why when non-obvious.

Never convert NOT_RUN into NOT_APPLICABLE to improve the report.

## 7. Final gate checklist

Evaluate explicitly in `## Quality Gate Evaluation`:

| Gate | Result | Evidence |
|---|---|---|
| Stage 08 verified PASS | PASS/FAIL | ... |
| P0 risk coverage complete | PASS/FAIL | ... |
| P1 risk coverage complete | PASS/FAIL | ... |
| Critical business rules tested | PASS/FAIL/N/A | ... |
| Core API/integration paths tested | PASS/FAIL/N/A | ... |
| Auth/authz denial paths tested | PASS/FAIL/N/A | ... |
| Stage 08 security regressions tested | PASS/FAIL/N/A | ... |
| Data constraints/migrations tested | PASS/FAIL/N/A | ... |
| Critical frontend/E2E paths tested | PASS/FAIL/N/A | ... |
| Canonical/full relevant suite passes | PASS/FAIL/NOT_RUN | ... |
| No unresolved confirmed product defects | PASS/FAIL | ... |
| No unresolved known flaky critical tests | PASS/FAIL | ... |
| Critical NOT_RUN count = 0 or equivalent evidence approved | PASS/FAIL | ... |
| Evidence validator passes | PASS/FAIL/NOT_RUN | ... |

Top-level PASS requires every applicable mandatory gate to pass.

## 8. Critical NOT_RUN policy

A required P0/P1 `NOT_RUN` item blocks PASS.

If another automated layer can credibly prove the same risk, update the traceability model before finalization so that the risk obligation points to the executed evidence. Do not leave a critical suite marked `NOT_RUN` and use equivalent evidence as a loophole.

Example: if browser tooling is unavailable but backend authorization is fully proven by API integration tests, authorization risk can map to the API evidence. Browser routing remains a separate UI requirement; if browser routing itself is P0/P1, Stage 09 remains blocked until it is executed.

## 9. Evidence consistency rules

Before finalizing, verify:
- plan test IDs appear in results or are explicitly NOT_RUN/N/A;
- results counts agree with command output where known;
- summary status agrees with results verdict;
- P0/P1 covered counts cannot exceed totals;
- failed suite count cannot coexist with top-level PASS;
- unresolved failures array must be empty for PASS;
- unresolved flaky test array must be empty for PASS;
- critical NOT_RUN array must be empty for PASS;
- next stage is `10-qa-debugging` only for PASS;
- `project-state.json` Stage 09 status agrees with summary.

Run `scripts/validate_stage09_evidence.py` when possible.

## 10. Final response format

The human-facing completion response should be concise compared with the artifacts, but include:
- test scope;
- commands run;
- defects fixed;
- final counts/critical coverage;
- remaining blockers/not-run items;
- artifact paths.

Then emit exactly one pair.

Success:

`STAGE_09_STATUS: PASS`
`NEXT_STAGE: 10-qa-debugging`

Not ready for downstream stage:

`STAGE_09_STATUS: BLOCKED`
`NEXT_STAGE: NONE`
