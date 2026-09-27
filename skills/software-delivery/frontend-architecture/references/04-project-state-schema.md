# Project State Contract for Stage 03

## Merge policy

`project-state.json` may already have an orchestrator-specific shape. Preserve all unknown keys and existing stage records.

Use the existing container type for `completed_stages` when clear. Do not rewrite the entire file to force this schema.

When no Stage 03 convention exists, use the canonical stage record below as the content model.

## Canonical Stage 03 record

```json
{
  "id": "03",
  "name": "frontend-architecture",
  "status": "PASS",
  "started_at": "ISO-8601 timestamp",
  "completed_at": "ISO-8601 timestamp",
  "artifacts": [
    {
      "path": "docs/03-frontend-architecture.md",
      "kind": "stage-report",
      "status": "created-or-updated"
    },
    {
      "path": "docs/03-frontend-quality.json",
      "kind": "verification-evidence",
      "status": "created-or-updated"
    }
  ],
  "decisions": [
    {
      "id": "D03-001",
      "decision": "Short decision statement",
      "rationale": "Why this choice fits prior stages and repository constraints",
      "impact": ["routing", "state", "stage-04"]
    }
  ],
  "assumptions": [
    {
      "id": "A03-001",
      "class": "ASSUMED_SAFE",
      "statement": "Assumption",
      "evidence": "Why it is safe",
      "needs_follow_up": false
    }
  ],
  "risks": [
    {
      "id": "R03-001",
      "severity": "low|medium|high|critical",
      "statement": "Residual risk",
      "mitigation": "Current mitigation or next-stage action",
      "blocking": false
    }
  ],
  "verification": {
    "lint": {
      "status": "PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
      "command": "actual command",
      "evidence": "summary/path"
    },
    "typecheck": {
      "status": "PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
      "command": "actual command",
      "evidence": "summary/path"
    },
    "tests": {
      "status": "PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
      "command": "actual command",
      "evidence": "summary/path"
    },
    "build": {
      "status": "PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
      "command": "actual command",
      "evidence": "summary/path"
    },
    "runtime_smoke": {
      "status": "PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
      "evidence": "routes/observations"
    },
    "responsive_rtl": {
      "status": "PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
      "evidence": "widths/locales/inspection"
    },
    "accessibility": {
      "status": "PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
      "evidence": "manual/automated results"
    },
    "security_hygiene": {
      "status": "PASS|FAIL|NOT_RUN|NOT_APPLICABLE",
      "evidence": "review summary"
    }
  },
  "handoff": {
    "next_stage": "04-backend-architecture",
    "backend_contracts": [],
    "integration_contracts": [],
    "open_non_blocking_items": []
  }
}
```

## Status rules

When Stage 03 is blocked:

- set `status` to `BLOCKED`;
- do not set a fake `completed_at` if the workflow distinguishes blocked from completed; follow existing convention;
- include blocker details in risks or the repository's blocker field;
- set handoff next stage to `NONE` or the workflow-equivalent null value;
- record checks already executed truthfully.

## Timestamp rules

Use actual current timestamps when tool support provides them. Do not fabricate historical execution times.

## Artifact rules

List only artifacts that actually exist. Do not include planned files as completed artifacts.

## Decision/assumption rules

Record material decisions only. Avoid flooding project state with trivial code-level details that belong in commits or the Stage 03 report.

IDs should remain stable when updating an existing decision/risk. Append new IDs rather than renumbering unrelated existing records.
