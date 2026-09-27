# Stage 06 Documentation Template

## Contents
1. Executive engineering summary
2. Baseline and repository map
3. Source requirements and core journeys
4. Requirement-to-API traceability
5. API architecture and protocol decision
6. Endpoint/resource map
7. Request/response conventions
8. Error contract
9. Collection behavior
10. Idempotency and duplicate behavior
11. Concurrency/preconditions
12. File transfer rules
13. External dependencies and webhooks
14. Backend integration notes
15. Frontend integration notes
16. Production mock audit
17. OpenAPI synchronization
18. Validation and evidence
19. Baseline failures and Stage 06 regressions
20. Assumptions
21. Risks and unresolved items
22. Stage 07 handoff
23. Final quality-gate result

Use this structure for `docs/06-api-design.md`. Add sections when the project requires them, but do not remove applicable mandatory sections.

# Stage 06 - API Design and Integration

## 1. Executive engineering summary
- Stage scope:
- Result:
- Core journeys integrated:
- Major contract decisions:
- Remaining Stage 07 handoff:

## 2. Baseline and repository map
| Area | Location | Notes |
|---|---|---|
| Frontend |  |  |
| Backend |  |  |
| Application/use cases |  |  |
| Persistence |  |  |
| Shared types |  |  |
| Tests |  |  |
| OpenAPI |  |  |

### Baseline validation
| Check | Command/method | Result | Classification |
|---|---|---|---|
|  |  |  |  |

## 3. Source requirements and core journeys
| Requirement ID | Actor | Journey/use case | Type | API required | Notes |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 4. Requirement-to-API traceability
| Requirement ID | Frontend entry | API operation | Handler | Use case/service | Persistence/dependency | Response consumer | Evidence | Status |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |

## 5. API architecture and protocol decision
- Existing architecture:
- Selected transport style:
- Why this preserves or improves the existing architecture:
- DTO/schema authority:
- OpenAPI authority: contract-first/code-first
- Versioning decision:
- Compatibility implications:

## 6. Endpoint/resource map
| Operation ID | Method | Path | Purpose | Success | Expected errors | Idempotent/retry-safe |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## 7. Request/response conventions
Document:
- identifiers;
- date/time/timezone;
- money/decimal;
- enums;
- required/optional/nullable behavior;
- naming convention;
- empty/no-content behavior.

## 8. Error contract
- Envelope/problem-details strategy:
- Machine error code strategy:
- Field validation format:
- Safe message strategy:
- Request/correlation ID behavior:

### Error mapping
| Failure class | HTTP status | Error code | Retryable | Frontend behavior |
|---|---:|---|---|---|
|  |  |  |  |  |

## 9. Collection behavior
- Pagination style:
- Default limit:
- Maximum limit:
- Stable ordering/tie-breaker:
- Filters:
- Sorting:
- Search:
- Field selection:

## 10. Idempotency and duplicate behavior
For every retry-prone mutation record:
| Operation | Key required | Scope | Fingerprint | Duplicate same payload | Same key different payload | Retention |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## 11. Concurrency/preconditions
| Operation/resource | Race risk | Strategy | Client conflict behavior |
|---|---|---|---|
|  |  |  |  |

## 12. File transfer rules
If applicable record upload/download type, media limits, size limits, storage indirection, scanning/security hook points, streaming/presigned behavior, and errors.

## 13. External dependencies and webhooks
| Dependency | Operation | Timeout | Retry owner | Duplicate protection | Failure mapping |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 14. Backend integration notes
For each core route identify controller/handler -> application use case -> persistence/external adapter. Record any earlier-layer correction and why it was necessary.

## 15. Frontend integration notes
Record:
- shared client/service location;
- base URL/environment behavior;
- DTO/type strategy;
- error normalization;
- query/mutation state strategy;
- cancellation/stale response handling;
- cache invalidation/update behavior.

## 16. Production mock audit
| Candidate | Production reachable | Decision | Evidence |
|---|---|---|---|
|  |  |  |  |

## 17. OpenAPI synchronization
- Location:
- Authority model:
- Generation/validation command:
- Route/schema synchronization result:
- Compatibility/diff result when relevant:

## 18. Validation and evidence
| Check/flow | Command or method | Scope | Result | Evidence summary | Classification |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 19. Baseline failures and Stage 06 regressions
### Pre-existing failures
- None, or list with evidence.

### Stage 06 regressions
- Must be zero for PASS.

## 20. Assumptions
- Assumption:
  - reason:
  - risk:
  - validation/follow-up:

## 21. Risks and unresolved items
| Risk/item | Impact | Stage 06 blocking | Owner/next action |
|---|---|---|---|
|  |  |  |  |

## 22. Stage 07 handoff
Record authentication/authorization/security items intentionally deferred without weakening existing controls.

## 23. Final quality-gate result
- Predecessor integrity: PASS/FAIL
- Coverage and traceability: PASS/FAIL
- Contract quality: PASS/FAIL
- Implementation integrity: PASS/FAIL
- OpenAPI integrity: PASS/FAIL/NA
- Validation integrity: PASS/FAIL
- Artifact integrity: PASS/FAIL
- Final decision: PASS/BLOCKED
