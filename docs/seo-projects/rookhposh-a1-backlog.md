# Rookhposh A1 — Evidence-Based SEO Backlog

Generated 2026-09-26 (Gregorian) / 1405-07-04 (Jalali). This is a planning-only backlog; no source remediation was performed.

## Owner decision required

The public homepage clearly supports a consumer virtual-try-on acquisition intent. The available evidence does not establish whether Rookhposh also sells the service to clothing stores. The owner must select one of:

1. consumer virtual try-on;
2. B2B clothing-store service;
3. both, with separate landing-page architecture.

Search Console, Analytics, ranking, traffic, and volume data are not available.

## Initial team plan

The evidence-based plan is SEO Manager, SEO Specialist, Frontend, DevOps, Tester, and Reviewer. Backend, Security, Docs, and UX are not selected for the initial remediation scope because no findings currently require them. Related properties must be planned independently.

## Prioritized work

| ID | Priority | Finding | Responsible role | Verification |
|---|---|---|---|---|
| ROOKHPOSH-SEO-001 | MEDIUM | Primary canonical not observed | Frontend | Raw and rendered HTML |
| ROOKHPOSH-SEO-002 | MEDIUM | Primary `robots.txt` returned 404 | DevOps | Bounded HTTP and source check |
| ROOKHPOSH-SEO-003 | MEDIUM | Primary `sitemap.xml` returned 404 | DevOps | Bounded HTTP/XML check |
| ROOKHPOSH-SEO-004 | MEDIUM | Primary title heuristic flagged length 27 | Frontend / SEO | Intent-approved metadata review |
| ROOKHPOSH-SEO-005 | LOW | Two primary images lack `alt` | Frontend | Raw and rendered HTML |
| ROOKHPOSH-SEO-006 | MEDIUM | Dashboard has four metadata/on-page findings | SEO Manager | Confirm ownership, then separate audit |
| ROOKHPOSH-SEO-007 | BLOCKED | Blog DNS resolution failed | DevOps | Repeat DNS/HTTPS check |

The backlog is recorded for later delegation through the existing task and approval workflow. It does not authorize code changes or deployment.
