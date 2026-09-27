# Required Artifacts and Stage 05 Handoff

## Table of contents

1. Required files
2. Architecture document structure
3. Evidence JSON contract
4. Stage 05 handoff JSON contract
5. Project-state update
6. Final response contract

## 1. Required files

Before PASS, create/update:

- `docs/04-backend-architecture.md`
- `docs/04-backend-architecture.evidence.json`
- `docs/04-stage05-handoff.json`
- `project-state.json`

Use equivalent existing docs directory only if repository convention strongly requires it; if paths differ, record them in `project-state.json` and ensure the validator can be given/updated for that repository. Prefer the canonical paths for orchestration reliability.

## 2. Architecture document structure

`docs/04-backend-architecture.md` must include headings covering at least:

1. Stage context and source artifacts
2. Repository reconnaissance
3. Existing stack and backend root
4. Requirements traceability summary
5. Architecture decision and rationale
6. Module map and ownership
7. Dependency/layer rules
8. Domain model and critical invariants
9. Application use cases
10. Authorization and tenant model
11. Repository ports
12. External service ports
13. Transaction boundaries
14. Idempotency and concurrency decisions
15. Transport/API boundary
16. Validation and error model
17. Configuration and secrets
18. Logging/observability/health
19. Background jobs/events and reliability decisions
20. Testing strategy and executed verification
21. Material decisions/ADRs and rejected alternatives
22. Assumptions, risks, and deferred work
23. Stage 05 handoff summary
24. Changed implementation/files summary

Keep it evidence-based. Link to real code paths.

## 3. Evidence JSON contract

Create valid JSON similar to:

```json
{
  "stage": "04-backend-architecture",
  "status": "PASS",
  "generated_at": "2026-01-01T00:00:00Z",
  "backend_root": "apps/api",
  "commands": [
    {
      "kind": "test",
      "command": "npm test -- --runInBand",
      "cwd": "apps/api",
      "status": "PASS",
      "exit_code": 0,
      "summary": "42 tests passed"
    }
  ],
  "checks": {
    "stage03_precondition": "PASS",
    "requirement_traceability": "PASS",
    "domain_application_boundary": "PASS",
    "transport_boundary": "PASS",
    "authorization_model": "PASS",
    "persistence_abstraction": "PASS",
    "stage05_boundary_respected": "PASS"
  },
  "changed_files": [],
  "warnings": [],
  "residual_risks": []
}
```

Use current timestamps if available. Do not fabricate results.

Allowed command status values: `PASS`, `FAIL`, `NOT_RUN`.

A PASS stage must not contain unresolved mandatory command failures.

## 4. Stage 05 handoff JSON contract

Create valid JSON with this conceptual shape:

```json
{
  "stage": "04-backend-architecture",
  "next_stage": "05-database-architecture",
  "modules": [
    {
      "name": "orders",
      "tenant_scope": "tenant",
      "aggregates_or_consistency_boundaries": ["Order"],
      "repository_ports": [
        {
          "name": "OrderRepository",
          "operations": ["findById", "save"],
          "consistency": "strong for state transitions",
          "transaction_participation": true
        }
      ],
      "transaction_boundaries": [
        {
          "use_case": "ApproveOrder",
          "atomic_requirements": ["order state change", "approval audit record"]
        }
      ],
      "uniqueness_requirements": [],
      "query_patterns": [],
      "concurrency_requirements": [],
      "idempotency_requirements": [],
      "retention_and_audit": [],
      "sensitive_data": []
    }
  ],
  "cross_module_atomicity": [],
  "event_outbox_candidates": [],
  "existing_persistence_to_reconcile": [],
  "assumptions": [],
  "risks": [],
  "blocked_questions": []
}
```

Use names and fields that match the actual project. Add fields when useful; do not remove the semantics Stage 05 needs.

Do not define final tables, columns, indexes, foreign keys, or migrations in this file.

## 5. Project-state update

Preserve unknown keys.

Update or append Stage 04 state with:

- stage ID;
- status;
- timestamp when available;
- artifact paths;
- backend root;
- material decisions;
- assumptions;
- risks;
- verification summary;
- next stage.

Follow `references/11-project-state-schema.md`.

## 6. Final response contract

Keep the user/orchestrator response concise relative to the actual work. Include:

- what was implemented/refactored;
- key architecture decisions;
- checks actually run and result summary;
- residual risks/deferred items;
- Stage 05 handoff readiness;
- blocker details if blocked.

End with exact completion markers from `SKILL.md`.
