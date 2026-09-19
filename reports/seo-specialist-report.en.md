# SEO Specialist — Engineering Report

| Field | Value |
|---|---|
| Project | AI-Engineer |
| Report type | SEO Specialist implementation |
| Language | English |
| Gregorian date | 2026-09-19 |
| Jalali date | 1405-06-28 |
| Delivery status | Implemented and validated |

## SEO Specialist Role

`seo_specialist` is a persistent, read-only employee integrated with the existing SEO Manager, role registry, task DAG, message bus, handoff protocol, work queues and project memory. It performs detailed analysis and verification; production changes remain owned by existing engineering and documentation roles.

## Capabilities and finding format

The role supports technical SEO, on-page SEO, intent and keyword analysis, clustering, keyword-to-page mapping, cannibalization detection, content gaps and briefs, internal linking, structured data, indexability/crawlability review and post-implementation verification. `SEOFinding` records category, severity, resource, description, evidence, impact, recommended action, responsible role, acceptance criteria, verification method, priority and status.

## Workflows and handoffs

- Technical and on-page observations become persisted evidence messages.
- Clusters and page mappings are project-scoped and flag duplicate targets as `cannibalization`.
- Content gaps and briefs are proposals to the SEO Manager.
- Implementation requests create normal existing coordination tasks, queue items and handoffs to the responsible role.
- Verification compares observed and expected output. A mismatch persists `SEO_FAILED` plus a revision handoff; matching evidence persists `SEO_VERIFIED`.
- Verified results can promote project memory through the existing evidence-gated memory store.

## Permissions and safety

The role has `READ_ONLY` permission and `writable_scope=none`; no production write tool is exposed. Unsourced ranking, traffic, Search Console, analytics, search-volume, CPC, difficulty, indexation and Core Web Vitals claims are marked `DATA SOURCE REQUIRED` rather than presented as facts. Project IDs are enforced for analysis, verification and memory promotion.

## Database and APIs

No new tables or parallel APIs were introduced. Existing SQLite coordination messages, tasks, queue records, handoffs and experience memories persist all outputs. The existing role listing API exposes the canonical role after service reload.

## Tests

Eleven deterministic orchestrator tests cover role/profile permissions, technical findings, on-page analysis, keyword clustering and isolation, content gaps/briefs, internal-link validation, implementation requests, verification/revision and memory promotion, false analytics prevention, and cross-project isolation. The complete orchestrator suite ran 224 tests and passed with one pre-existing skipped test; Model Gateway ran 26 tests and passed; Local Agent ran 2 tests and passed.

## Known limitations

External crawler, analytics, Search Console, ranking and Core Web Vitals providers are not implicitly connected. Those facts remain unavailable until an authorized evidence source is supplied. The specialist prepares requests and verification records but does not modify application source or publish external changes.

