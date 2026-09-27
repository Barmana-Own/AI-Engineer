# Project State Contract

## Table of Contents

1. Principles
2. Minimum shape
3. Source record
4. Decision record
5. Assumption record
6. Risk record
7. Open question record
8. Conflict record
9. Evidence record
10. Review finding record
11. Stage quality record
12. Stage status semantics

## 1. Principles

- Preserve unknown top-level and nested keys.
- Keep `schema_version: "1.0"` for compatibility with the wider workflow.
- Keep stable IDs; do not renumber existing items.
- Store material facts, decisions, assumptions, risks, evidence, questions, conflicts, and review findings as structured records.
- Keep canonical prose in Stage 01 documents and synchronize state records that downstream automation needs.
- Add Stage 01 to `workflow.completed_stages` only after PASS.
- A BLOCKED or IN_PROGRESS stage is not completed.
- Never overwrite unrelated state owned by other stages.

## 2. Minimum shape

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "Example",
    "summary": "One-sentence product definition"
  },
  "workflow": {
    "current_stage": "01-project-analysis-prompt-engineering",
    "next_stage": "02-design-system-ui-architecture",
    "stage_records": {
      "01-project-analysis-prompt-engineering": {
        "status": "IN_PROGRESS",
        "artifacts": [],
        "quality": {
          "score": null,
          "hard_gates_passed": false,
          "open_critical_findings": 0,
          "open_high_findings": 0,
          "blocking_questions": 0,
          "validator_passed": false
        },
        "updated_at": "ISO-8601 timestamp"
      }
    },
    "completed_stages": []
  },
  "sources": [],
  "decisions": [],
  "assumptions": [],
  "risks": [],
  "open_questions": [],
  "conflicts": [],
  "evidence": [],
  "review_findings": []
}
```

## 3. Source record

```json
{
  "id": "SRC-001",
  "locator": "User brief, file path, document id, URL, or source reference",
  "type": "USER_BRIEF|USER_MESSAGE|PROJECT_FILE|CONTRACT|SPECIFICATION|REPOSITORY_DOC|API_DOC|EXTERNAL_OFFICIAL|EXISTING_STAGE_ARTIFACT",
  "authority": "PRIMARY|ACCEPTED_INTERNAL|AUTHORITATIVE_EXTERNAL|SECONDARY|ASSUMPTION_ONLY",
  "freshness": "YYYY-MM-DD or unknown",
  "covers": ["scope", "workflow"]
}
```

## 4. Decision record

```json
{
  "id": "DEC-001",
  "statement": "...",
  "rationale": "...",
  "source": "USER|EXISTING_ARTIFACT|RESEARCH|ASSUMPTION|MIXED",
  "source_refs": ["SRC-001"],
  "confidence": "HIGH|MEDIUM|LOW",
  "evidence_ids": [],
  "affected_ids": []
}
```

## 5. Assumption record

```json
{
  "id": "ASM-001",
  "statement": "...",
  "impact": "HIGH|MEDIUM|LOW",
  "confidence": "HIGH|MEDIUM|LOW",
  "status": "OPEN|VALIDATED|REJECTED",
  "temporary": true,
  "affected_ids": [],
  "validation_owner": "USER|CLIENT|STAGE_02|LATER_STAGE"
}
```

## 6. Risk record

```json
{
  "id": "RSK-001",
  "category": "PRODUCT|BUSINESS|SECURITY|PRIVACY|COMPLIANCE|INTEGRATION|DELIVERY|TECHNICAL",
  "statement": "...",
  "likelihood": "HIGH|MEDIUM|LOW",
  "impact": "HIGH|MEDIUM|LOW",
  "trigger": "...",
  "mitigation": "...",
  "contingency": "...",
  "owner": "Stage or role when known",
  "affected_ids": [],
  "status": "OPEN|MITIGATED|ACCEPTED|CLOSED"
}
```

## 7. Open question record

```json
{
  "id": "Q-001",
  "question": "...",
  "blocking": false,
  "why_it_matters": "...",
  "temporary_assumption_id": "ASM-001",
  "owner": "USER|CLIENT|STAGE_02|LATER_STAGE",
  "affected_ids": [],
  "status": "OPEN|ANSWERED|DEFERRED"
}
```

## 8. Conflict record

```json
{
  "id": "CONFLICT-001",
  "topic": "...",
  "sources": ["SRC-001", "SRC-002"],
  "resolution": "...",
  "status": "RESOLVED|OPEN",
  "blocking": false,
  "affected_ids": []
}
```

## 9. Evidence record

```json
{
  "id": "EVD-001",
  "claim": "...",
  "source_title": "...",
  "source_locator": "URL, document id, standard id, or authoritative source reference",
  "publisher": "...",
  "checked_at": "YYYY-MM-DD",
  "authority_level": "PRIMARY|OFFICIAL_SECONDARY|REPUTABLE_SECONDARY",
  "confidence": "HIGH|MEDIUM|LOW",
  "affected_ids": []
}
```

## 10. Review finding record

```json
{
  "id": "FINDING-001",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "status": "OPEN|RESOLVED|DEFERRED",
  "statement": "...",
  "affected_ids": [],
  "resolution": "...",
  "owner": "..."
}
```

## 11. Stage quality record

Update the Stage 01 record with the final readiness information:

```json
{
  "score": 97,
  "hard_gates_passed": true,
  "open_critical_findings": 0,
  "open_high_findings": 0,
  "blocking_questions": 0,
  "validator_passed": true,
  "review_artifact": "docs/01-readiness-review.md",
  "validation_artifact": "docs/01-stage01-validation.json"
}
```

Do not fabricate the score. It must match `docs/01-readiness-review.md`.

## 12. Stage status semantics

Allowed Stage 01 statuses:
- `IN_PROGRESS`
- `PASS`
- `BLOCKED`

For PASS:
- quality score must be >=95;
- hard gates must pass;
- open critical/high findings must be 0;
- blocking questions must be 0;
- validator must pass when tools are available;
- `current_stage` becomes `02-design-system-ui-architecture`;
- `next_stage` becomes `02-design-system-ui-architecture`;
- Stage 01 appears exactly once in `completed_stages`;
- the Stage 01 artifact list contains all required canonical outputs.

For BLOCKED:
- `current_stage` remains Stage 01;
- `next_stage` is `null`;
- Stage 01 must not appear as completed;
- blocker must be explicit in the risk/question/conflict records.
