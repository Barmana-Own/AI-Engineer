# SEO Engine

AI-Engineer now includes a platform-neutral SEO capability under
`services/orchestrator/app/seo_engine/`. It is a capability of the existing
Company/Supervisor workflow, not a second agent framework or project database.

## Supported inputs

- public URL with bounded same-host crawling;
- source-code workspace inspection;
- combined URL and source evidence;
- WordPress REST through a server-side, draft-first adapter.

Platform detection recognizes WordPress, React/Vite, React SPA, Next.js,
Express, static sites, and generic web pages. Detection records evidence and
uncertainty rather than assuming an unknown framework.

## Evidence and safety

Audits persist raw-page evidence, optional rendered evidence, content hashes,
status codes, metadata, links, headings, image-alt gaps, structured-data
signals, and provenance. Crawls enforce page/depth/response limits, same-host
scope, timeout limits, redirect checks, and private-network rejection unless a
future controlled local adapter explicitly enables it. Search Console results
are labeled `real`, `mock`, or `no_data`; the engine never fabricates traffic,
rankings, volume, CPC, or indexing claims.

## Workflow

1. Company Director/Supervisor identifies an SEO objective.
2. `seo_manager` owns strategy, priorities, acceptance criteria, and gates.
3. `seo_specialist` performs audit, keyword/intent mapping, and verification.
4. Findings become existing AI-Engineer tasks through the Skill Router.
5. Frontend/backend/DevOps/docs/test roles implement or verify within their
   existing permissions and Local Agent boundary.
6. Re-audit evidence updates the finding to `verified` or `failed`.

The current repository does not yet expose a real Agent Worker/Local Agent
execution chain, so task delegation is persisted but is not represented as a
completed live worker run.

## API

- `POST /v1/seo/sites` — register a site profile.
- `POST /v1/seo/sites/{id}/detect-platform` — detect from source or supplied
  HTML.
- `POST /v1/seo/sites/{id}/audits` — create a bounded audit snapshot.
- `GET /v1/seo/sites/{id}/findings` — list evidence-backed findings.
- `POST /v1/seo/sites/{id}/keywords` — normalize, cluster, map, and brief.
- `POST /v1/seo/sites/{id}/findings/{finding_id}/delegate` — create an
  existing project task with routed skills.
- `POST /v1/seo/sites/{id}/findings/{finding_id}/verify` — record re-audit
  evidence and set the quality-gate status.

All persisted SEO records retain `project_id` and `site_id` boundaries. The
existing AI-Engineer SQLite database is authoritative; no `project-state.json`
is introduced.

## Readiness and limitations

The bounded SEO capability is integrated (`SEO_ENGINE_INTEGRATED = YES`) and is covered by
persistence/API/unit/integration tests. The following gates remain intentionally open:

- `REACT_NODE_SEO_READY = NO`: the repository does not yet expose the real Agent Worker → Model Gateway → Local Agent execution chain required for a live implementation task.
- `WORDPRESS_SEO_READY = NO`: the server-side REST adapter is draft-first and direct publish is disabled; credentialed live verification and Rank Math integration were not run.
- `READY_FOR_REAL_SEO_PROJECT = NO`: Search Console live data, browser-rendered Playwright capture, and a real worker-driven repair/re-audit cycle still require deployment of the missing worker runtime.

The existing SQLite database remains authoritative. No second project-state store, task system, authentication system, or agent framework is introduced.
## Final hardening notes

Persisted SEO site profiles are rehydrated by their database id after an Orchestrator restart; the router regression test exercises this path. SEO API list fields and verification evidence have bounded per-item lengths. The outbound client streams responses and caps accumulated bytes before parsing.
The audit evidence API also exposes persisted page evidence and compares a baseline snapshot with a later snapshot using finding category/resource/title keys. Comparison output is evidence only; it does not claim rankings or traffic improvement.