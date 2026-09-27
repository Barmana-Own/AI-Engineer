# Project State Contract for Stage 02

Use this contract whenever Stage 02 reads or updates `project-state.json`.

## Principles

- Preserve unknown top-level and nested keys.
- Preserve Stage 01 records and stable shared IDs.
- Use `schema_version: "1.0"` unless an authoritative project schema says otherwise.
- Treat `workflow.stage_records` as the authoritative per-stage status map.
- Treat `workflow.completed_stages` as an append/dedupe history, not a free-form notes field.
- A BLOCKED or IN_PROGRESS stage is not completed.
- Do not erase decisions, assumptions, risks, conflicts, evidence, or questions created by earlier stages.
- Add Stage 02-specific shared records only when they are materially needed by later stages.

## Stage identity

- Current stage id: `02-design-system-ui-architecture`
- Next stage id: `03-frontend-architecture`
- Allowed statuses: `IN_PROGRESS`, `PASS`, `BLOCKED`

## Minimum compatible shape

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "Example",
    "summary": "One-sentence product definition"
  },
  "workflow": {
    "current_stage": "02-design-system-ui-architecture",
    "next_stage": "03-frontend-architecture",
    "stage_records": {
      "01-project-analysis-prompt-engineering": {
        "status": "PASS",
        "artifacts": []
      },
      "02-design-system-ui-architecture": {
        "status": "IN_PROGRESS",
        "artifacts": [],
        "updated_at": "ISO-8601 timestamp"
      }
    },
    "completed_stages": []
  },
  "decisions": [],
  "assumptions": [],
  "risks": [],
  "open_questions": [],
  "conflicts": [],
  "evidence": []
}
```

## PASS transition

When Stage 02 passes:

- set Stage 02 record status to `PASS`;
- include the required Stage 02 artifacts in its record;
- set `workflow.current_stage` to `03-frontend-architecture`;
- set `workflow.next_stage` to `03-frontend-architecture`;
- ensure Stage 02 appears exactly once in `workflow.completed_stages` with status PASS and completion time;
- preserve the Stage 01 completed record.

## IN_PROGRESS transition

When Stage 02 is active but not complete:

- set Stage 02 record status to `IN_PROGRESS`;
- set `workflow.current_stage` to `02-design-system-ui-architecture`;
- set `workflow.next_stage` to `03-frontend-architecture`;
- ensure Stage 02 is absent from completed stages.

## BLOCKED transition

When a true blocker exists:

- set Stage 02 record status to `BLOCKED`;
- keep `workflow.current_stage` at Stage 02;
- set `workflow.next_stage` to `null`;
- ensure Stage 02 is absent from completed stages;
- record the blocker as a risk, question, or conflict with enough detail for recovery.

## Shared records

Reuse the Stage 01 record shapes for `DEC-*`, `ASM-*`, `RSK-*`, `Q-*`, `CONFLICT-*`, and `EVD-*`.

When adding Stage 02 decisions, use the next unused stable ID in the shared sequence rather than starting a second conflicting sequence.
