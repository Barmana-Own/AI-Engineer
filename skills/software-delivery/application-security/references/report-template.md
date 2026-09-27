# Stage 08 Security Review Report Template

Use this structure for `docs/08-security-review.md`. Keep it evidence-based and concise enough to be actionable. Add subsections when the project requires them, but do not remove mandatory sections.

## Table of contents

1. Executive summary and scope
2. Repository baseline and architecture
3. Threat model and coverage matrix
4. Findings and domain reviews
5. Fixes, verification and residual risk
6. Stage 09 handoff and gate decision

```markdown
# Stage 08 - Application Security Review

## 1. Executive summary
- Gate status: PASS | FAIL | BLOCKED
- Review date/time:
- Repository/branch/HEAD:
- Scope summary:
- Critical: N
- High: N
- Medium: N
- Low: N
- Info: N
- Fixed during Stage 08: N
- Residual risks: N
- Blocking dependency, if any:

One paragraph explaining the final security posture and whether Stage 09 may proceed.

## 2. Authorization and scope
| Target | Environment | Scope class | Active testing | Notes |
|---|---|---|---|---|

Explicitly state that unrelated/third-party systems were not actively tested unless separately authorized.

## 3. Repository baseline
- Stage 07 status/artifact reviewed:
- Git branch/HEAD:
- Worktree status before Stage 08:
- Pre-existing modified/untracked files:
- Detected stack/services:
- Test/build/lint commands:

## 4. Architecture and attack surface
### 4.1 Roles and identities
### 4.2 Entry points
### 4.3 Sensitive assets/data
### 4.4 Trust boundaries
### 4.5 External dependencies/integrations

## 5. Threat model and priority abuse cases
| Abuse case | Asset/action | Actor | Trust boundary | Existing control | Risk priority |
|---|---|---|---|---|---|

## 6. Coverage matrix
| Domain | Status (VERIFIED/FINDING/N/A) | Evidence/Findings | Notes |
|---|---|---|---|
| Authentication/session/recovery | | | |
| Authorization/tenant isolation | | | |
| API/business logic | | | |
| Input/injection | | | |
| Browser/XSS/CSRF/CORS | | | |
| SSRF/outbound requests | | | |
| Files/paths/parsers | | | |
| Sensitive data/crypto/secrets | | | |
| Dependencies/supply chain | | | |
| Runtime/container/deployment | | | |
| Logging/errors/auditability | | | |
| Webhooks/integrations | | | |

Every N/A requires a concrete reason.

## 7. Findings summary
| ID | Severity | Confidence | Status | Component | Title |
|---|---|---|---|---|---|

## 8. Detailed findings

### SEC-001 - [Title]
- Severity:
- Confidence:
- Status:
- Affected component/endpoint:
- Location:
- Actors/tenants/prerequisites:
- Security invariant:
- Evidence (redacted):
- Impact:
- Root cause:
- Remediation:
- Regression test:
- Retest result:
- Standards mapping (optional):
- Residual risk/notes:

Repeat for each material finding. Low/Info observations may be summarized when no remediation detail is needed.

## 9. Authentication and authorization review
Summarize account/session/token lifecycle and object/property/function/tenant authorization conclusions, including negative test coverage.

## 10. API and business-logic review
Summarize state-transition, replay/idempotency, concurrency, abuse-control, bulk/export and economic-state conclusions where applicable.

## 11. Input/browser/files/outbound review
Summarize injection, XSS, CSRF/CORS, SSRF, file/path/parser and redirect conclusions.

## 12. Sensitive data, secrets and cryptography
Summarize sensitive-data flows, secret locations reviewed, frontend/log leakage checks and cryptographic observations. Do not include secret values.

## 13. Dependency and supply-chain review
| Tool/command | Status | Result |
|---|---|---|

List material advisories with project-specific reachability/exposure conclusions and upgrades performed.

## 14. Runtime/container/deployment review
Summarize production mode, privilege, ports, proxies, service exposure, health/debug surfaces and deployment secret handling.

## 15. Logging, errors and auditability
Summarize security-event coverage, redaction and client-error leakage.

## 16. Security fixes and changed files
| File | Change | Related finding |
|---|---|---|

State that pre-existing unrelated user changes were preserved, or describe any unavoidable overlap.

## 17. Verification results
| Command/test | Status | Purpose/result |
|---|---|---|

Use RUN/PASS/FAIL/NOT_RUN accurately. Include targeted security regression tests and broader regression/build checks.

## 18. Residual risks and limitations
For each residual risk include severity, exposure, compensating control, owner/follow-up and why the gate decision remains valid or invalid.

List environmental/tool limitations separately from technical vulnerabilities.

## 19. Stage 09 handoff
- Security regression tests Stage 09 must preserve:
- High-risk flows needing broader QA:
- Test identities/fixtures needed:
- Known limitations/environment needs:
- No-go areas/third-party scope constraints:

## 20. Gate checklist
- [ ] No unremediated Critical/High within project control
- [ ] Material auth/authorization boundaries verified
- [ ] Material fixes have regression tests and retest evidence
- [ ] Dependency/secrets/runtime reviews complete or limitations explicit
- [ ] Broader relevant regression/build checks complete
- [ ] Final diff reviewed
- [ ] Findings JSON consistent with report
- [ ] project-state updated
- [ ] Artifact validator passed when runnable

## 21. Final decision
`STAGE_08_STATUS: PASS|FAIL|BLOCKED`
`SECURITY_GATE: CLEARED|NOT_CLEARED`
`NEXT_STAGE: 09-software-testing|NONE`
```
