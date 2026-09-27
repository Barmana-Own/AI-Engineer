# Project Brief Template

## Table of Contents

1. Project identity and framing
2. Scope and release intent
3. Roles and journeys
4. Business rules and modules
5. Integrations and domains
6. Security, constraints, uncertainty, and direction
7. Stage 02 handoff summary

Use these headings in `docs/01-project-brief.md`. Keep IDs stable after first assignment. Prefer structured records over long narrative prose.

# [Project Name] — Stage 01 Project Brief

## 1. Project Identity
- Project name: ...
- One-sentence product definition: ...
- Analysis mode: DISCOVERY|SPECIFICATION|RESUME|REPAIR
- Primary source(s): SRC-...
- Product context: ...

## 2. Executive Summary

Explain what the product is, who it serves, why it exists, and the intended outcome in concise product language.

## 3. Product Objective

Capture business/product outcomes and success signals. Label proposed measures as assumptions when not supplied.

## 4. Problem Statement

Describe the current problem, affected actors, current friction, and intended improvement. Separate problems from proposed features.

## 5. Scope

### In Scope

List explicit capabilities/outcomes included in this stage baseline.

### Out of Scope

List explicit exclusions and deferred capabilities.

### Optional / Future Scope

List non-required ideas without allowing them to become MUST requirements.

### Release / MVP Intent

State the smallest coherent release intent when the source supports release sequencing; otherwise state that release slicing is not yet confirmed.

## 6. Target Users and Roles

Use one block per material actor:

### ROLE-001 — [Role name]
- Responsibility: ...
- Goals: ...
- Core actions: ...
- Data / permission intent: ...
- Important interactions: ROLE-... / SYSTEM / None
- Related journeys: JRN-...
- Source refs: SRC-... / ASM-...
- Confidence: HIGH|MEDIUM|LOW

## 7. Primary User Journeys

Use one block per material end-to-end flow:

### JRN-001 — [Journey name]
- Trigger: ...
- Initiating actor: ROLE-...|SYSTEM
- Preconditions: ...
- Normal path:
  1. ...
  2. ...
- Alternate paths: ... or None
- Exception / failure paths: ... or None
- Outcome / resulting state: ...
- Related roles: ROLE-...
- Related rules: BR-...
- Related modules: MOD-...
- Related integrations: INT-... or None
- Source refs: SRC-... / ASM-...
- Confidence: HIGH|MEDIUM|LOW

## 8. Business Rules

Use one block per enforceable rule/invariant:

### BR-001 — [Rule name]
- Rule: ...
- Applies when: ...
- Exception: ... or None
- Affects: JRN-..., FR-...
- Source refs: SRC-... / EVD-... / ASM-...
- Confidence: HIGH|MEDIUM|LOW

## 9. Core Modules

Use logical product responsibilities, not premature service boundaries.

### MOD-001 — [Module name]
- Responsibility: ...
- Primary roles: ROLE-...
- Journeys supported: JRN-...
- Data domains: DOM-...
- Integrations: INT-... or None
- Notes: ...

## 10. External Integrations

Summarize INT-* records and point to `docs/01-domain-integration-map.md` for the canonical integration detail.

## 11. Major Data Domains

Summarize DOM-* records and point to `docs/01-domain-integration-map.md` for the canonical conceptual domain detail.

## 12. Initial Security and Privacy Concerns

Capture trust boundaries, sensitive data classes, privileged actions, likely abuse cases, audit needs, access concerns, and compliance questions at requirement level only. Reference NFR/RSK/Q IDs.

## 13. Constraints

Separate confirmed constraints from assumptions. Cover only relevant technical, business, legal, platform, schedule, localization, compatibility, contractual, or operational constraints.

## 14. Assumptions

Summarize ASM-* and point to `docs/01-risk-register.md` as canonical detail.

## 15. Decisions

Summarize material DEC-* and point to `docs/01-risk-register.md` as canonical detail.

## 16. Risks

Summarize highest-impact RSK-* and point to `docs/01-risk-register.md` as canonical detail.

## 17. Open Questions

Summarize Q-* and clearly identify blockers. Point to `docs/01-risk-register.md` as canonical detail.

## 18. Conflicts

Summarize CONFLICT-* and resolution status. Point to `docs/01-risk-register.md` as canonical detail.

## 19. Initial Technical Direction

Record only broad direction required to constrain later stages: platform class, broad architecture constraints already fixed, localization/RTL, offline/realtime needs, device constraints, integration style, or operational conditions.

Do not select detailed service boundaries, database schemas, endpoint designs, infrastructure topology, or implementation code here.

## 20. Stage 02 Handoff Summary

Point to `docs/01-stage-02-handoff.md` and list only the highest-impact Stage 02 constraints and guardrails.
