# Stage 05 Documentation and Project-State Contract

## `docs/05-database-architecture.md`

Use these headings in this order:

1. `# Stage 05 - Database Architecture`
2. `## Executive status`
3. `## Inputs and Stage 04 traceability`
4. `## Detected persistence stack`
5. `## Data-domain and entity model`
6. `## Relationship and ownership model`
7. `## Invariant and constraint matrix`
8. `## Physical schema conventions`
9. `## Table responsibilities`
10. `## Index and query-path matrix`
11. `## Transaction boundaries`
12. `## Concurrency and idempotency controls`
13. `## Audit, deletion, retention, and sensitive data`
14. `## Migration plan and recovery strategy`
15. `## Seed and fixture strategy`
16. `## Persistence adapter coverage`
17. `## Validation evidence`
18. `## Migration/query-plan evidence`
19. `## Assumptions and unresolved risks`
20. `## Stage 04 compatibility amendments`
21. `## Stage 06 handoff`
22. `## Quality-gate result`

Tables are preferred for matrices. Include real file paths and commands where useful.

## Validation evidence format

For each check record:
- check name;
- status: PASS/FAIL/NOT_RUN/UNVERIFIED/N/A;
- evidence type: OBSERVED/EXECUTED/INFERRED/ASSUMED/BLOCKED;
- command or source path;
- concise observed result;
- follow-up if failed.

Never fabricate timestamps, row counts, command output, or query plans.

## `project-state.json`

Preserve unknown existing keys. Update or append Stage 05 using the project's existing schema when compatible.

If no stage-state convention exists, use a structure logically equivalent to:

```json
{
  "completed_stages": {
    "05-database-architecture": {
      "status": "PASS",
      "evidence_level": "executed",
      "artifacts": [],
      "decisions": [],
      "assumptions": [],
      "risks": [],
      "validation": {
        "executed": [],
        "not_run": [],
        "failed": []
      },
      "compatibility_amendments": [],
      "next_stage": "06-api-integration"
    }
  }
}
```

Do not force this exact shape onto a repository that already has an established compatible state schema.

## Status semantics

- `PASS`: complete quality gate with sufficient evidence.
- `BLOCKED`: failed prerequisite or true external dependency prevents safe completion.
- `IN_PROGRESS` or repository-equivalent: implementation exists but critical verification remains incomplete.

Do not place an IN_PROGRESS stage under a collection that semantically means only completed stages; follow the repository's state structure.
