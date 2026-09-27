# Project State Contract for Stage 06

## Contents
1. Goals
2. Compatibility principle
3. Locating Stage 05
4. Canonical Stage 06 record
5. Completed stages behavior
6. Atomic update procedure
7. Validation rules

## 1. Goals

`project-state.json` is orchestration state, not a scratchpad. Update it deterministically while preserving unknown keys and prior-stage records.

## 2. Compatibility principle

Projects may already use one of several state layouts. Do not destructively migrate the entire file during Stage 06.

Recognize Stage 05 from compatible structures such as:
- `stages["05"].status`;
- a stage object in `stages` array with id `05`;
- an object in `completed_stages` with id/stage `05` and status `PASS`;
- a string `05` or canonical Stage 05 name in `completed_stages` only when the repository's prior stages clearly use that convention.

Prefer explicit status fields over inference.

If multiple records conflict, treat predecessor state as inconsistent and investigate artifacts before proceeding.

## 3. Locating Stage 05

Stage 05 verification order:
1. explicit stage record with ID `05` and status `PASS`;
2. explicit completed-stage object with ID `05` and PASS;
3. repository-established equivalent confirmed by earlier stage artifacts.

Do not infer PASS merely because database files exist.

## 4. Canonical Stage 06 record

When the current state model permits stage objects, store an equivalent of:

```json
{
  "id": "06",
  "name": "api-integration",
  "status": "PASS",
  "started_at": "ISO-8601 timestamp when available",
  "completed_at": "ISO-8601 timestamp when available",
  "artifacts": [
    "docs/06-api-design.md",
    "docs/openapi.yaml"
  ],
  "requirement_coverage": {
    "covered": 0,
    "partial": 0,
    "blocked": 0,
    "not_applicable": 0
  },
  "decisions": [],
  "assumptions": [],
  "risks": [],
  "validation": [
    {
      "command": "...",
      "status": "PASS",
      "scope": "..."
    }
  ],
  "blockers": [],
  "next_stage": "07-authentication-authorization"
}
```

Adapt key placement to the repository's existing state layout. Do not create duplicate competing state systems.

## 5. Completed stages behavior

If `completed_stages` exists:
- add Stage 06 only when status is PASS;
- do not add Stage 06 as completed when BLOCKED;
- avoid duplicate entries;
- preserve order/convention used by prior stages;
- preserve unknown fields on existing objects.

## 6. Atomic update procedure

1. Read and parse current JSON.
2. Keep an in-memory copy of unknown keys.
3. Apply Stage 06 update only after final gate decision.
4. Write valid JSON to a temporary file when tool/runtime permits.
5. Re-parse the temporary output.
6. Replace the original only after parse success.
7. Run `scripts/validate_project_state.py`.

If writing fails after implementation, do not claim clean PASS until state/artifact integrity is restored.

## 7. Validation rules

Stage 06 PASS state must include or allow derivation of:
- stage ID/name;
- PASS status;
- artifacts;
- decisions/assumptions/risks or repository equivalent;
- validation evidence summary;
- next stage.

Stage 06 BLOCKED state should include:
- BLOCKED status;
- blocker category/reason;
- evidence;
- minimum unblock action;
- next stage NONE.

Never store secrets or raw credentials in state.
