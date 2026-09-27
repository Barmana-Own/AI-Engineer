# Traceability and Change Control

## Table of Contents

1. Canonical source rule
2. Stable IDs
3. Traceability graph
4. Change classes
5. Change procedure
6. Deletion and deprecation
7. Conflict resolution
8. Resume and repair behavior

## 1. Canonical source rule

Use canonical artifacts as the source of truth:
- product/scope/roles/journeys/rules: `docs/01-project-brief.md`;
- requirements: `docs/01-requirements.md`;
- domains/integrations: `docs/01-domain-integration-map.md`;
- assumptions/decisions/risks/questions/conflicts: `docs/01-risk-register.md` and synchronized state;
- traceability: `docs/01-traceability-matrix.md`;
- external evidence: `docs/01-research-evidence.md` when present;
- readiness findings: `docs/01-readiness-review.md`;
- downstream directive: `docs/01-stage-02-handoff.md`.

Do not let duplicated summary text silently become a competing source of truth.

## 2. Stable IDs

Once assigned, keep IDs stable across revisions.

Do not renumber surviving records to close gaps.

When an item is replaced:
- preserve the old ID in history/deprecation note;
- create a new ID only when the semantic identity changed materially;
- update all references.

## 3. Traceability graph

Maintain these relationships where applicable:

`SOURCE/EVD/ASM/DEC -> ROLE/JRN/BR/INT/DOM -> FR/NFR -> Stage 02 concern`

Also maintain:
- ROLE -> JRN;
- JRN -> FR;
- BR -> FR;
- INT -> FR/NFR;
- RSK -> affected IDs;
- ASM -> affected IDs;
- EVD -> affected IDs.

Every relationship need not be one-to-one. The objective is to eliminate unexplained behavior and dangling requirements.

## 4. Change classes

### Class A - Editorial

Meaning does not change.

Examples:
- typo correction;
- formatting;
- clearer wording with identical semantics.

Action:
- update artifact;
- no DEC required.

### Class B - Clarification

Meaning becomes more precise without changing scope.

Examples:
- acceptance criterion sharpened;
- ambiguous term defined;
- dependency link added.

Action:
- update artifact and traceability;
- DEC optional unless downstream work already depended on the ambiguity.

### Class C - Material product change

Scope, rule, behavior, priority, integration, actor responsibility, or quality target changes.

Action:
1. create/update DEC-* with rationale and source;
2. update affected canonical artifacts;
3. update traceability;
4. update risks/assumptions/questions;
5. rerun adversarial review and validation.

### Class D - Conflict repair

New source contradicts accepted material content.

Action:
1. create CONFLICT-*;
2. preserve both positions;
3. resolve using source precedence or safe reversible interpretation;
4. record resolution and affected IDs;
5. rerun affected analysis.

## 5. Change procedure

For any Class C/D change:
1. identify trigger/source;
2. identify affected IDs before editing;
3. record decision/conflict;
4. edit canonical source artifact;
5. propagate references;
6. update project state;
7. regenerate/review handoff if design-affecting;
8. rerun validation;
9. ensure no stale duplicated summary remains.

## 6. Deletion and deprecation

Do not silently delete accepted requirements or decisions.

When removing an item:
- record reason;
- identify replacement when any;
- remove or update all references;
- ensure the removal does not orphan a journey, rule, or integration;
- preserve the audit trail in DEC/CONFLICT/readiness notes when material.

## 7. Conflict resolution

Use source precedence:
1. explicit current user instruction;
2. accepted project contract/artifact;
3. authoritative current external source;
4. professional assumption.

Do not use external research to override an explicit product preference unless the preference is impossible, unsafe, unlawful, or factually incompatible with a fixed external constraint. In that case, create a conflict and explain the constraint.

## 8. Resume and repair behavior

On RESUME:
- inspect IDs and decisions before adding new ones;
- continue numbering without renumbering;
- preserve accepted scope;
- repair missing links rather than rewriting everything.

On REPAIR:
- constrain edits to defects and their affected graph;
- do not use a validation issue as justification for unrelated scope changes;
- rerun only the necessary analysis plus full final gates.
