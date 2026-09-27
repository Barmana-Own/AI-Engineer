# Readiness Review Template

Create `docs/01-readiness-review.md` after drafting all other Stage 01 artifacts.

# Stage 01 Readiness Review — [Project Name]

## Review Metadata
- Execution mode: DISCOVERY|SPECIFICATION|RESUME|REPAIR
- Reviewed artifacts: ...
- Machine validator executed: YES|NO
- Machine validator result: PASS|FAIL|NOT_AVAILABLE
- Review date: YYYY-MM-DD

## Quality Score

| Category | Max | Score | Rationale |
|---|---:|---:|---|
| Product framing and scope | 12 | 0 | ... |
| Actors, journeys, business rules | 18 | 0 | ... |
| Functional requirements | 20 | 0 | ... |
| Non-functional requirements | 12 | 0 | ... |
| Domain, integrations, security, privacy | 12 | 0 | ... |
| Traceability and evidence | 12 | 0 | ... |
| Risk and uncertainty management | 6 | 0 | ... |
| Stage 02 handoff quality | 8 | 0 | ... |
| **TOTAL** | **100** | **0** | |

## Hard Gate Checklist

Use this exact table. `N/A` is allowed only when the gate is genuinely conditional; explain why.

| Gate | Result | Evidence / rationale |
|---|---|---|
| GATE-01 Required artifacts complete | PASS|FAIL | ... |
| GATE-02 Stable IDs unique | PASS|FAIL | ... |
| GATE-03 No dangling references | PASS|FAIL | ... |
| GATE-04 FR contract complete | PASS|FAIL | ... |
| GATE-05 NFR contract complete | PASS|FAIL | ... |
| GATE-06 MUST requirements supported/testable | PASS|FAIL | ... |
| GATE-07 Major journeys covered by FRs | PASS|FAIL | ... |
| GATE-08 Confirmed integrations covered | PASS|FAIL|N/A | ... |
| GATE-09 Research-derived requirements evidenced | PASS|FAIL|N/A | ... |
| GATE-10 No blocking open questions | PASS|FAIL | ... |
| GATE-11 No open CRITICAL/HIGH findings | PASS|FAIL | ... |
| GATE-12 Stage 02 handoff ready and boundary-safe | PASS|FAIL | ... |
| GATE-13 State synchronized | PASS|FAIL | ... |
| GATE-14 Machine validator passes | PASS|FAIL|N/A | ... |
| GATE-15 Strict-pass validator after commit | PASS|FAIL|N/A | ... |

Before the final state commit, GATE-15 may temporarily be N/A with rationale `Performed after PASS state commit`. After strict validation succeeds, update it to PASS if the workflow persists a post-commit readiness review. The strict validator itself remains authoritative for this gate.

## Quality Attribute Review

For each materially relevant attribute from `references/quality-attribute-catalog.md`, record `APPLICABLE|NOT_APPLICABLE|DEFERRED`, related NFR IDs, and rationale.

## Conditional Domain Lens Review

List each applied domain lens and the material omissions it helped test. If no lens applies, state why.

## Adversarial Findings

### FINDING-001 — [Short title]
- Severity: CRITICAL|HIGH|MEDIUM|LOW
- Status: OPEN|RESOLVED|DEFERRED
- Finding: ...
- Affected IDs / artifacts: ...
- Resolution: ...
- Owner if deferred: ...

## Remaining Open Questions

List Q-* and confirm that no blocking question remains for PASS.

## Stage Boundary Audit

Confirm that Stage 01 did not create wireframes, visual design, physical DB schema, API implementation, production infrastructure, or application code.

## Final Recommendation

- Recommended status: PASS|REPAIR_REQUIRED|BLOCKED
- Quality score: NN/100
- Open CRITICAL findings: N
- Open HIGH findings: N
- Blocking questions: N
- Repair summary / blocker: ...
