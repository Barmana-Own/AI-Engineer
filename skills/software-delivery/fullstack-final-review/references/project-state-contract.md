# Project State and Stage 11 Contract

## Stage 11 proof hierarchy

Use this order of trust:
1. current `project-state.json` entry for Stage 11 plus matching Stage 11 artifact;
2. explicit Stage 11 artifact with PASS marker that clearly belongs to the active project/revision;
3. narrative references from later chat/docs only as supporting context, not sole proof.

## Contradiction handling

Examples:
- project-state says FAIL, report says PASS → G00 FAIL until reconciled;
- project-state says PASS but report contains blocking unresolved finding → treat as stale/contradictory and fail precondition;
- Stage 11 report is from a different branch/release → not valid proof;
- Stage 11 state missing but explicit valid artifact exists → reconstruct state and record recovery.

Never invent a Stage 11 PASS from absence of errors.

## Updating project-state.json

Preserve unknown top-level and nested keys. Do not rewrite the file into a smaller schema.

Add/update Stage 12 information with fields conceptually like:

```json
{
  "stage_id": 12,
  "name": "fullstack-final-review",
  "status": "PASS",
  "artifacts": ["docs/12-final-review.md", "release-manifest.json"],
  "decisions": [],
  "assumptions": [],
  "risks": [],
  "repairs": [],
  "next_stage": null
}
```

Adapt to the existing state file structure rather than forcing duplicate incompatible fields.

## Failure ownership

When Stage 12 fails, identify the earliest stage materially responsible for the blocker. Examples:
- approved core requirement absent → requirement/implementation owning stage;
- API implementation drift → API/backend stage;
- schema migration broken → data stage;
- auth bypass → security/backend stage;
- tests invalid → QA/test stage;
- deployment cannot start → deployment/ops stage.

Stage 12 remains the reporting stage but `NEXT_STAGE` should point to the owning repair stage.
