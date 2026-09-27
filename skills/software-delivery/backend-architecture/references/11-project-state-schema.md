# Project State Schema Guidance

## Purpose

Maintain orchestration state without destroying fields owned by other stages or tools. Treat this as a compatibility contract, not a reason to rewrite the entire state file.

## Rules

1. Parse the existing JSON before editing.
2. Preserve unknown top-level and nested keys.
3. Do not reorder or normalize unrelated data solely for aesthetics when avoidable.
4. Do not remove earlier stage history.
5. Use the repository's existing state shape when it is coherent.
6. If no coherent Stage 04 representation exists, use the canonical shape below.
7. Keep machine-readable values stable: stage ID `04-backend-architecture`, status `PASS` or `BLOCKED`, next stage `05-database-architecture` on success.

## Canonical shape

A compatible example:

```json
{
  "workflow": {
    "current_stage": "05-database-architecture",
    "last_completed_stage": "04-backend-architecture"
  },
  "completed_stages": [
    {
      "id": "04-backend-architecture",
      "status": "PASS",
      "artifacts": [
        "docs/04-backend-architecture.md",
        "docs/04-backend-architecture.evidence.json",
        "docs/04-stage05-handoff.json"
      ],
      "backend_root": "apps/api",
      "decisions": [],
      "assumptions": [],
      "risks": [],
      "verification": {
        "evidence": "docs/04-backend-architecture.evidence.json"
      },
      "next_stage": "05-database-architecture"
    }
  ]
}
```

## Existing alternative shapes

If `completed_stages` is an object/map instead of a list, preserve that style and update the `04-backend-architecture` entry.

If the state file uses numeric stage IDs, preserve compatibility while still storing the canonical stage name inside the Stage 04 entry when possible.

## BLOCKED behavior

Do not insert a false PASS record.

Record a blocked stage in the repository's in-progress/blocked field if one exists, or add a compatible field such as:

```json
{
  "blocked_stage": {
    "id": "04-backend-architecture",
    "status": "BLOCKED",
    "blockers": []
  }
}
```

Keep `NEXT_STAGE` effectively none until the blocker is resolved.
