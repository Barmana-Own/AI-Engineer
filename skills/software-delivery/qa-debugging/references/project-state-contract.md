# Stage 10 Project-State Contract

## Table of contents

1. Purpose
2. Preservation rule
3. Stage record
4. Recommended payload
5. Merge behavior
6. Status rules
7. Artifacts and risks
8. Script usage
9. Validation

## 1. Purpose

`project-state.json` is the orchestrator's cross-stage ledger. Stage 10 must update it without erasing unrelated or unknown keys.

## 2. Preservation rule

Never replace the entire state file with a hand-written minimal object when an existing state file is present.

Preserve:

- unknown top-level keys;
- earlier stage records;
- project identifiers;
- architecture/product decisions;
- external orchestration metadata.

Only mutate the keys needed to record Stage 10 and next-stage status.

## 3. Stage record

Represent Stage 10 with enough information for Stage 11 and the master orchestrator to understand readiness.

Recommended fields:

- `stage_id`: `10`
- `stage_name`: `qa-debugging`
- `status`: `PASS` or `BLOCKED`
- `completed_at`: ISO-8601 timestamp when available
- `artifacts`: paths produced
- `summary`: concise factual status
- `decisions`: material decisions
- `assumptions`: non-critical assumptions used
- `risks`: remaining risks
- `known_issues`: unresolved issue IDs
- `blockers`: blocker IDs/descriptions
- `verification`: final command/result summaries
- `next_stage`: `11-deployment-production` on PASS, otherwise `null`

Adapt to an existing project-state schema when one is already established. Do not force a conflicting parallel schema if earlier stages use another convention.

## 4. Recommended payload

When no established per-stage schema exists, a payload file for `scripts/update_project_state.py` may look like:

```json
{
  "stage_id": 10,
  "stage_name": "qa-debugging",
  "status": "PASS",
  "artifacts": [
    "docs/10-qa-matrix.md",
    "docs/10-qa-report.md",
    "docs/10-known-issues.md"
  ],
  "summary": "Release-critical journeys and mandatory Stage 10 gates passed in the documented test environment.",
  "decisions": [],
  "assumptions": [],
  "risks": [],
  "known_issues": [],
  "blockers": [],
  "verification": [],
  "next_stage": "11-deployment-production"
}
```

## 5. Merge behavior

The bundled update script follows conservative behavior:

- parse existing JSON when present;
- preserve unknown keys;
- preserve earlier `completed_stages` entries;
- replace an existing Stage 10 record rather than duplicating it;
- append Stage 10 to `completed_stages` on PASS when the existing schema uses that array;
- remove Stage 10 from `completed_stages` on BLOCKED if represented as stage records;
- update a `stages` object/list when compatible;
- set `current_stage`/`next_stage` only when those keys exist or when the state has no established stage-navigation convention.

Always inspect the resulting diff/state before accepting it.

## 6. Status rules

Only `PASS` or `BLOCKED` are valid Stage 10 orchestrator statuses.

On PASS:

- next stage is `11-deployment-production`.

On BLOCKED:

- next stage is null/none according to existing schema;
- blockers must be non-empty.

Do not write PASS while the QA report declares an open P0/P1.

## 7. Artifacts and risks

Record actual paths that exist. Do not list hypothetical artifacts.

Remaining P2/P3 issues should appear in `known_issues` or risks according to the project-state schema.

Critical missing external evidence that blocks release belongs in `blockers`.

## 8. Script usage

Preferred usage:

```bash
python scripts/update_project_state.py \
  --state project-state.json \
  --stage-payload .stage10-state.json
```

The script creates a backup beside the state file by default before writing unless `--no-backup` is supplied.

After running:

- inspect the JSON;
- inspect source control diff when available;
- confirm unknown keys and earlier stages remain.

## 9. Validation

Before PASS verify:

- valid JSON;
- Stage 10 status matches report;
- artifact paths match actual files;
- next stage matches status;
- blockers/known issues agree with reports;
- no earlier-stage record was lost.
