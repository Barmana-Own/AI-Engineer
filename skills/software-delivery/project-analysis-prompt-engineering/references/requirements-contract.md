# Requirements Contract

## Table of Contents

1. Purpose
2. Priority vocabulary
3. Source and confidence vocabulary
4. Functional requirement contract
5. Acceptance criteria rules
6. Non-functional requirement contract
7. Requirement quality rules
8. Traceability summary

## 1. Purpose

Use the exact block shapes below in `docs/01-requirements.md`. Stable fields make requirements readable by humans, downstream agents, and validators.

## 2. Priority vocabulary

- `MUST`: required for the defined product scope, an explicit accepted decision, or a confirmed constraint.
- `SHOULD`: important but deferrable without invalidating the core product outcome.
- `COULD`: optional enhancement. Never let a COULD silently become MVP/MUST scope.

Do not use MUST merely to mean "important".

## 3. Source and confidence vocabulary

Source:
- `USER`
- `EXISTING_ARTIFACT`
- `RESEARCH`
- `ASSUMPTION`
- `MIXED`

Confidence:
- `HIGH`
- `MEDIUM`
- `LOW`

Use `Source refs` to identify the concrete support such as `SRC-001`, `DEC-001`, `ASM-001`, or `EVD-001`.

## 4. Functional requirement contract

```markdown
### FR-001 — Short action-oriented title
- Actor: ROLE-001
- Priority: MUST
- Requirement: The system shall ...
- Acceptance criteria:
  - Observable pass/fail condition.
  - Another observable condition when materially needed.
- Related: JRN-001, MOD-001, BR-001
- Dependencies: None
- Source: USER
- Source refs: SRC-001
- Confidence: HIGH
- Evidence: None
- Assumptions: None
- Notes: None
```

Rules:
- express one primary behavior;
- use externally observable outcomes;
- `Actor` may be `ROLE-*` or `SYSTEM`;
- `Related` must include at least one `JRN-*` or `MOD-*` unless the requirement is genuinely global;
- use stable IDs in Dependencies/Related where possible;
- if Source includes RESEARCH, Evidence must include EVD-*;
- if Source includes ASSUMPTION, Assumptions must include ASM-*;
- if Source is USER/EXISTING_ARTIFACT, Source refs should point to SRC-* or DEC-* that preserves the accepted source;
- avoid implementation prescriptions unless the implementation choice itself is an explicit constraint.

## 5. Acceptance criteria rules

Acceptance criteria must make the requirement falsifiable.

Good criteria specify observable conditions such as:
- accepted input leads to a defined state/outcome;
- invalid input is rejected with defined behavior;
- unauthorized actor cannot perform the action;
- duplicate/retry does not create unintended duplicate effects;
- failure of a material external dependency leads to a defined recoverable/error state;
- a state transition is persisted/visible/auditable as required.

Use bullet criteria or Given/When/Then style. Do not use criteria such as:
- "works correctly";
- "is user friendly";
- "is secure";
- "loads fast";
- "handles errors";
without a verifiable condition.

Do not force irrelevant error/security criteria into every requirement.

## 6. Non-functional requirement contract

```markdown
### NFR-001 — Short quality title
- Category: SECURITY
- Priority: MUST
- Target: A measurable target or an explicitly assumed validation target.
- Verification: How a later stage can prove the target.
- Related: SYSTEM or MOD-001, JRN-001
- Dependencies: None
- Source: ASSUMPTION
- Source refs: ASM-001
- Confidence: MEDIUM
- Evidence: None
- Assumptions: ASM-001
- Notes: None
```

Recommended categories:

`SECURITY`, `PRIVACY`, `PERFORMANCE`, `AVAILABILITY`, `RESILIENCE`, `SCALABILITY`, `ACCESSIBILITY`, `LOCALIZATION`, `OBSERVABILITY`, `MAINTAINABILITY`, `COMPATIBILITY`, `BACKUP_RECOVERY`, `AUDITABILITY`, `DATA_INTEGRITY`, `USABILITY`, `PORTABILITY`.

Do not fabricate SLA, RTO, RPO, throughput, retention, regulatory, accessibility, or compliance targets. If a target is required for downstream planning but not supplied, create the smallest reasonable ASM-* and keep the target explicitly provisional.

## 7. Requirement quality rules

Before accepting a requirement, test it against all of these questions:

1. Is it atomic enough to pass/fail independently?
2. Is the actor/system responsibility clear?
3. Is the behavior or quality externally verifiable?
4. Is its priority justified by scope/source?
5. Is it free of unnecessary implementation detail?
6. Does it duplicate or contradict another requirement?
7. Does it reference the journey/module/rule/integration it supports?
8. Is uncertainty visible through ASM/Q/EVD rather than hidden in prose?
9. Could a later test engineer derive tests from it without guessing the intended outcome?
10. Would removing this requirement leave an uncovered journey, rule, integration, or quality need?

Split compound requirements joined by independent "and" clauses when the parts could fail separately.

## 8. Traceability summary

End the requirements document with:

```markdown
## Traceability Summary

| Requirement | Actor/System | Journey/Module | Business Rule / Integration | Source refs | Confidence |
|---|---|---|---|---|---|
| FR-001 | ROLE-001 | JRN-001 / MOD-001 | BR-001 | SRC-001 | HIGH |
```

This table is a compact index, not a replacement for `docs/01-traceability-matrix.md`.
