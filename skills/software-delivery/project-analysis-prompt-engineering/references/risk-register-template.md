# Risk Register Template

Create `docs/01-risk-register.md` with this structure.

# Stage 01 Risk, Assumption & Decision Register — [Project Name]

## Assumptions

### ASM-001 — [Short title]
- Statement: ...
- Impact: HIGH|MEDIUM|LOW
- Confidence: HIGH|MEDIUM|LOW
- Status: OPEN|VALIDATED|REJECTED
- Temporary / reversible: YES|NO
- Affected IDs: ...
- Validation owner / stage: ...
- Source: ASSUMPTION or mixed source explanation

## Decisions

### DEC-001 — [Short title]
- Statement: ...
- Rationale: ...
- Source: USER|EXISTING_ARTIFACT|RESEARCH|ASSUMPTION|MIXED
- Confidence: HIGH|MEDIUM|LOW
- Evidence IDs: ... or None
- Affected IDs: ...

## Risks

### RSK-001 — [Short title]
- Category: PRODUCT|BUSINESS|SECURITY|PRIVACY|COMPLIANCE|INTEGRATION|DELIVERY|TECHNICAL
- Statement: ...
- Likelihood: HIGH|MEDIUM|LOW
- Impact: HIGH|MEDIUM|LOW
- Trigger / early signal: ...
- Mitigation direction: ...
- Contingency / fallback: ... when known
- Owner / responsible stage: ...
- Affected IDs: ...
- Status: OPEN|MITIGATED|ACCEPTED|CLOSED

## Open Questions

### Q-001 — [Short title]
- Question: ...
- Blocking: true|false
- Why it matters: ...
- Temporary assumption: ASM-...|None
- Owner: USER|CLIENT|STAGE_02|LATER_STAGE
- Affected IDs: ...
- Status: OPEN|ANSWERED|DEFERRED

## Source Conflicts

### CONFLICT-001 — [Short topic]
- Position A: ...
- Source A: SRC-... / source reference
- Position B: ...
- Source B: SRC-... / source reference
- Impact: ...
- Resolution: ...
- Status: RESOLVED|OPEN
- Blocking: true|false
- Affected IDs: ...
