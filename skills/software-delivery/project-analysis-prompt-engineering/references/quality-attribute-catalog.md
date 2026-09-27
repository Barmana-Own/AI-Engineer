# Quality Attribute Catalog

Use this catalog during NFR analysis. It is a consideration checklist, not a requirement generator. Add an NFR only when the attribute is relevant to the product.

| Attribute | Questions to consider | Example verification direction |
|---|---|---|
| SECURITY | What must be protected from unauthorized action or disclosure? What privileged actions exist? | threat review, authorization tests, security test plan |
| PRIVACY | What personal/sensitive data exists? Who may see it? What lifecycle questions exist? | privacy review, access checks, lifecycle tests |
| PERFORMANCE | Which user/system operations are latency-sensitive? | percentile response/processing target, load test |
| AVAILABILITY | What functions must remain available and when? | service objective or operational test when confirmed |
| RESILIENCE | What happens when dependencies fail or requests are duplicated/retried? | fault injection, retry/degraded-mode tests |
| SCALABILITY | What dimensions may grow: users, tenants, files, events, jobs, transactions? | capacity/load test against assumed or confirmed scale |
| ACCESSIBILITY | Which accessibility level/platform obligations apply? | accessibility audit against confirmed standard |
| LOCALIZATION | Which languages, RTL/LTR, locale, calendar, currency, timezone behaviors matter? | locale matrix and UI/content tests |
| OBSERVABILITY | Which critical flows need logs, metrics, traces, alerts, or audit events? | observability checklist and incident drill |
| MAINTAINABILITY | What modularity/configurability/testability constraints matter? | architecture/code quality checks in later stages |
| COMPATIBILITY | Which browsers, OSes, devices, API versions, file formats matter? | compatibility test matrix |
| BACKUP_RECOVERY | Which data/state needs backup and what recovery expectations are confirmed? | restore test against confirmed/assumed RPO/RTO |
| AUDITABILITY | Which decisions/actions must be attributable and historically reconstructable? | audit-event coverage tests |
| DATA_INTEGRITY | Which records/calculations must remain consistent and duplicate-safe? | invariant and reconciliation tests |
| USABILITY | Which task-efficiency/error-prevention outcomes matter? Avoid vague "easy to use". | usability task completion criteria |
| PORTABILITY | Must the product move across environments/providers/platforms? | deployment/compatibility proof in later stages |
