# SEO Automation Source Import Report

| Package | Purpose | Important material | Runtime decision | Risk |
| --- | --- | --- | --- | --- |
| `seo-core` | Rules, normalization, clustering, content/link helpers | `packages/seo-core/src/index.ts` | Adapted to Python contracts and evidence models | Low when deterministic |
| `wordpress-client` | WordPress REST operations | `packages/wordpress-client/src/index.ts` | Draft-first adapter contract; publish remains blocked | High for credentials/publication |
| `rank-math-client` | Rank Math metadata integration | package source and tests | Optional provider boundary; not enabled by default | Medium |
| `search-console-client` | Search performance query contract | provider types and mock/real modes | Provider-neutral no-data/mock labels | High if credentials/claims are mishandled |
| `automation-core` / worker | Jobs, retries, scheduling | BullMQ processors | Not copied; existing autonomy/recovery remain authoritative | High concurrency risk |
| Prisma database | Standalone content/auth/team schema | `packages/database/prisma/schema.prisma` | Mapped only to additive SQLite SEO tables | High migration/data-boundary risk |
| Apps/API/UI | NestJS API and web application | `apps/*` | Retained for reference only; no second app is mounted | Medium duplication risk |

## Package inventory

The archive contains `SKILL.md`-style operational documentation only in its
repository guidance (`AGENTS.md`); it is primarily a TypeScript application
source archive. Source packages, tests, references, and assets were preserved
in the extraction workspace for review. Built `dist/` and archive `.git`
metadata are not imported into AI-Engineer runtime paths.

## Safety classification

- Pure validator: SEO rule and keyword helpers.
- Read-only inspector: HTML/source crawler and Search Console query adapter.
- Test runner: archive package test scripts; not exposed as model tools.
- Command runner: archive worker/build scripts; must route through Local Agent
  policy if used in a future adapter.
- Network check: WordPress/Search Console/HTTP clients; allowlist, timeout,
  same-host and SSRF policy required.
- Artifact writer: draft content/brief/report operations; writes remain scoped
  to declared project artifacts and approval gates.

No archive script is registered as an unrestricted model tool.
