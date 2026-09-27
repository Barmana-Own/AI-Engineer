# SEO Content Automation Integration Audit

## Scope

The supplied `seo-content-automation-phase-10` archive was inspected before
integration. Its useful material is an SEO playbook and provider contract
collection, not a replacement application for AI-Engineer.

## Reused and adapted concepts

| Archive capability | AI-Engineer integration decision |
| --- | --- |
| SEO rule checks, keyword normalization, intent clustering, briefs, and internal-link ranking | Reimplemented as bounded Python modules in `services/orchestrator/app/seo_engine/` so the existing FastAPI runtime remains authoritative. |
| WordPress REST client and Rank Math concepts | Draft-first `WordPressAdapter` contract with a deterministic mock; direct publication remains owner/approval gated. |
| Search Console query dimensions and provider modes | Provider-neutral contracts with explicit `real`, `mock`, and `no_data` semantics. |
| Playwright/rendered-page concepts | Raw evidence is supported now; rendered evidence can be injected by a trusted inspection adapter. No unrestricted browser tool is exposed. |
| Credential encryption, hostname allowlists, SSRF controls | Adapted into URL validation, same-host crawling, bounded response sizes, and no credential material in findings. |

## Replaced by existing AI-Engineer infrastructure

The archive's Prisma schema, standalone users/teams/authentication, NestJS
API, BullMQ worker, and separate project/task state are not copied. AI-Engineer
continues to own identity, roles, Company Director/Supervisor, Task DAG,
messages, approvals, Local Agent, Model Gateway, memory, recovery, and SQLite
persistence. SEO findings delegate through the existing `agent_tasks` table
and Skill Router.

## Platform coverage

The capability detects WordPress, Next.js, React/Vite, React SPA, Express,
static, and generic web sources from deterministic source and observed-HTML
signals. The public API supports URL-only, source-only, combined, and
WordPress-oriented site profiles. Project/site identifiers are persisted and
used to prevent cross-project finding leakage.

## Current readiness boundary

The SEO engine, persistence model, evidence crawler, keyword planning, draft
WordPress adapter, and delegation API are implemented. A production WordPress
credential adapter and a fully live Agent Worker/Local Agent execution chain
are outside this slice because the current repository does not contain the
real Worker Runtime described by earlier Phase 9 requests. The final report
must therefore keep real-project readiness explicitly `NO` until those
boundaries are verified with real services.

## Archive material retained

The extracted archive remains under the controlled audit workspace
`F:/phase9work/seo-content-automation-phase-10-source` for traceability. Its
source files, references, and assets were not silently deleted or presented as
active AI-Engineer runtime modules.
