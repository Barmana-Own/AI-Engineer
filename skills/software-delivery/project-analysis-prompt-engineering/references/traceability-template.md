# Traceability Matrix Template

Create `docs/01-traceability-matrix.md` with this structure. Include only applicable rows, but do not omit a required relationship because it is inconvenient.

# Stage 01 Traceability Matrix — [Project Name]

## Actor to Journey Coverage

| Actor | Journeys | Coverage note |
|---|---|---|

## Journey to Functional Requirement Coverage

| Journey | Functional Requirements | Exception coverage | Status |
|---|---|---|---|

Status: `COVERED|PARTIAL|MISSING`.

## Business Rule Enforcement

| Business Rule | Enforced by FR/NFR | Status |
|---|---|---|

## Module Coverage

| Module | FRs | NFRs | Primary roles/journeys |
|---|---|---|---|

## Integration Coverage

| Integration | FRs/NFRs | Failure behavior covered? | Evidence/Assumption | Status |
|---|---|---|---|---|

## Assumption Impact

| Assumption | Affected IDs | Risk if wrong | Validation owner/stage |
|---|---|---|---|

## Risk Impact

| Risk | Affected IDs | Mitigation owner/stage | Status |
|---|---|---|---|

## Evidence Coverage

| Evidence | Claim / affected IDs | Freshness | Confidence |
|---|---|---|---|

## Requirement Source Index

| Requirement | Actor/System | Journey/Module | Rule/Integration | Source | Confidence | Evidence/Assumption |
|---|---|---|---|---|---|---|

## Coverage Summary

Report:
- total ROLE/JRN/BR/MOD/INT/FR/NFR counts;
- journeys without FR coverage;
- confirmed integrations without FR/NFR coverage;
- rules without enforcement coverage;
- dangling references;
- material assumptions with no affected IDs;
- research-derived requirements without EVD-*;
- overall traceability status: `PASS|REPAIR_REQUIRED`.
