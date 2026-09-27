# Domain and Integration Map Template

Create `docs/01-domain-integration-map.md` with this structure.

# Domain & Integration Map — [Project Name]

## Canonical Vocabulary

| Term | Canonical Meaning | Source | Aliases / Avoid |
|---|---|---|---|

## Conceptual Data Domains

For each domain use:

### DOM-001 — [Name]
- Definition: ...
- Business ownership / related roles: ROLE-...
- Lifecycle summary: ...
- Sensitive data: NONE|LOW|MODERATE|HIGH with short rationale
- Related domains: DOM-...
- Authoritative source/system: ...
- Related journeys: JRN-...
- Source: USER|EXISTING_ARTIFACT|RESEARCH|ASSUMPTION|MIXED
- Confidence: HIGH|MEDIUM|LOW

Do not include table/column/index/schema design.

## External Integrations

For each integration use:

### INT-001 — [System / Provider]
- Purpose: ...
- Classification: CONFIRMED|ASSUMED|OPTIONAL
- Direction: INBOUND|OUTBOUND|BIDIRECTIONAL
- Interaction trigger/pattern: ...
- Conceptual data exchanged: ...
- Dependency / availability implication: ...
- Failure / retry / idempotency concern: ...
- Authentication / trust dependency: ... or Unknown / later stage
- Evidence / assumption: EVD-...|ASM-...|None
- Related requirements: FR-..., NFR-...
- Source: USER|EXISTING_ARTIFACT|RESEARCH|ASSUMPTION|MIXED
- Confidence: HIGH|MEDIUM|LOW

## Dependency Summary

Summarize dependencies that could block or materially constrain later design.

## Stage-Boundary Note

State that physical database schema, endpoint design, protocol implementation, infrastructure topology, and secret management are deferred.
