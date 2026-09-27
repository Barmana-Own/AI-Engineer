# Stage 01 Quality Gates and Scoring Rubric

## Table of Contents

1. Gate policy
2. Hard gates
3. 100-point rubric
4. Finding severity
5. Repair policy
6. PASS criteria
7. BLOCKED criteria

## 1. Gate policy

Quality is judged by both machine-verifiable structure and expert semantic review. Neither is sufficient alone.

A document can be syntactically valid and still fail because its requirements are vague, incomplete, unsupported, or unusable by Stage 02.

## 2. Hard gates

All hard gates must pass:

1. Required artifacts exist and contain no unresolved scaffold placeholders.
2. Stable IDs are unique within their namespaces.
3. No dangling cross-reference exists among canonical IDs.
4. Every FR has Actor, Priority, Requirement, Acceptance criteria, Related, Dependencies, Source, and Confidence.
5. Every NFR has Category, Priority, Target, Verification, Related, Dependencies, Source, and Confidence.
6. Every MUST FR has at least one acceptance criterion and a traceable source/decision/assumption.
7. Every major JRN has at least one FR.
8. Every confirmed INT has at least one FR/NFR or explicit constraint.
9. Every research-derived requirement links EVD-*.
10. Every blocking Q-* is resolved before PASS.
11. Every open CRITICAL/HIGH review finding is resolved before PASS.
12. Stage 02 handoff exists and does not perform Stage 02 work.
13. `project-state.json` is synchronized with canonical assumptions, decisions, risks, questions, conflicts, and evidence.
14. Machine validator passes when execution tools are available.
15. Strict-pass validator passes after state commit.

## 3. 100-point rubric

Score conservatively. Do not award full points for sections that merely exist.

### A. Product framing and scope - 12 points

- 3: product definition and problem are specific;
- 3: objectives/outcomes are clear;
- 4: in/out/optional scope is explicit and coherent;
- 2: release/MVP intent is clear when relevant.

### B. Actors, journeys, and business rules - 18 points

- 5: material actors and permission intent are covered;
- 7: primary, alternate, and material exception journeys are covered;
- 6: business rules/invariants are explicit and linked.

### C. Functional requirements - 20 points

- 6: requirements are atomic and observable;
- 6: acceptance criteria are testable and meaningful;
- 4: priorities are justified and not inflated;
- 4: requirements avoid implementation leakage and duplication.

### D. Non-functional requirements - 12 points

- 4: relevant quality attributes were considered;
- 4: targets/validation targets are measurable;
- 4: inferred targets are labeled and traceable.

### E. Domain, integrations, security, and privacy - 12 points

- 3: conceptual domains/terminology are coherent;
- 3: integrations/dependencies and failure implications are covered;
- 3: trust boundaries/sensitive data are identified;
- 3: material security/privacy/abuse concerns are represented.

### F. Traceability and evidence - 12 points

- 5: actor/journey/rule/module/integration coverage is traceable;
- 3: assumptions/decisions/risks link to affected items;
- 4: researched facts use evidence and appropriate confidence.

### G. Risk and uncertainty management - 6 points

- 2: material risks are explicit;
- 2: material assumptions are explicit;
- 2: conflicts/questions are handled without unnecessary blocking.

### H. Stage 02 handoff quality - 8 points

- 3: handoff is concise but sufficient;
- 2: scope guardrails and immutable decisions are explicit;
- 2: design-affecting IDs are referenced;
- 1: directives/prohibitions preserve stage boundaries.

## 4. Finding severity

### CRITICAL

A defect that makes the product contract unsafe or fundamentally unusable, such as:
- contradictory core scope;
- missing primary actor or core journey;
- unresolved blocking legal/security/compliance dependency;
- severe source conflict with no safe reversible path;
- PASS state despite known missing core behavior.

### HIGH

A defect likely to cause material downstream rework or incorrect product behavior, such as:
- major journey exception omitted;
- unsupported MUST requirement;
- confirmed integration with no failure behavior where failure is material;
- major permission boundary missing;
- material traceability gap;
- fabricated NFR target represented as confirmed.

### MEDIUM

A defect that reduces clarity or completeness but can usually be deferred without invalidating the stage, such as:
- secondary actor detail missing;
- acceptance criterion could be sharper;
- minor terminology inconsistency;
- non-critical assumption lacks owner.

### LOW

Editorial or low-impact consistency issue.

## 5. Repair policy

For each finding:
1. identify root cause;
2. identify canonical artifact to repair;
3. repair the source artifact, not only the review report;
4. update linked traceability/state if IDs or meaning changed;
5. mark finding RESOLVED with short resolution note;
6. rerun affected checks.

Do not fix symptoms only in the handoff while leaving canonical requirements incorrect.

## 6. PASS criteria

PASS requires all of the following:
- quality score >= 95/100;
- every hard gate passes;
- zero open CRITICAL findings;
- zero open HIGH findings;
- zero blocking open questions;
- machine validation passes when available;
- strict-pass validation passes after state commit;
- Stage 02 can proceed without the user restating the project.

A score >=95 does not override a failed hard gate.

## 7. BLOCKED criteria

Use BLOCKED only when a true external dependency prevents a trustworthy handoff and cannot be covered by a safe reversible assumption.

When blocked:
- state the exact blocker;
- identify affected IDs/artifacts;
- state what input or decision would unblock the stage;
- do not mark Stage 01 completed;
- do not set a next stage.
