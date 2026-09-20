# Corrective Phase 3 â€” Sales Intake and SEO Workflow Integration

| Field | Value |
|---|---|
| Project | AI-Engineer |
| Report type | Technical report |
| Phase | Corrective Phase 3 |
| Gregorian date | 2026-09-19 |
| Jalali date | 1405-06-28 |
| Delivery status | Implemented and validated on the remote repository |

## Scope

This phase connects the existing Sales, Requirements, Company Director, team-planning, SEO, and Supervisor components. No second agent, task, message, or memory framework was introduced. Opportunity intake now converts into the existing project and execution workflow, while SEO objectives influence the existing dynamic team plan.

## Sales intake flow

`ProjectOpportunity` records are processed through the existing persistence layer and move through explicit states: `NEW`, `ANALYZING`, `NEEDS_CLARIFICATION`, `QUALIFIED`, `REJECTED`, `WAITING_OWNER`, and `CONVERTED_TO_PROJECT`.

`OpportunityIntakeService` composes the existing `SalesAgent`, `RequirementsAgent`, `CompanyDirector`, and `Supervisor`. Sales produces an `OpportunityBrief`, client-needs summary, open questions, risks, recommended next action, and a proposal draft. Unsupported-fit or commercial-risk cases are held at the Human Owner gate; Sales cannot authorize legal, payment, fixed-price, deadline, or contract commitments.

## Opportunity-to-project flow

After qualification and any required owner approval, conversion creates a normal persisted project, creates a requirements handoff, obtains the existing dynamic team plan, and stores the converted project id on the opportunity. Starting execution calls the existing `Supervisor.start_objective`; no alternate execution path is used. Conversion is idempotent, including for isolated/test database paths.

## SEO routing flow

The existing `TeamPlanner` now detects SEO signals and distinguishes analysis/research from implementation. SEO objectives select `seo_manager` and `seo_specialist`; keyword/search-intent work can add `researcher` without adding engineering roles. Technical remediation adds only justified engineering roles such as `frontend`, `backend`, `devops`, `integration`, `tester`, `security`, or `docs`. The selected roles are used by the existing Supervisor task DAG, so unselected roles are not scheduled.

SEO Manager remains responsible for strategy, prioritization, delegation, acceptance criteria, and completion assessment. SEO Specialist performs detailed findings and verification. Engineering roles own production changes. Findings can create an existing SEO implementation task, fail verification, request revision, and then reach `SEO_VERIFIED` after the engineer fixes the fixture/workspace. Unavailable Search Console, Analytics, ranking, volume, CPC, backlink, and Core Web Vitals data remains unavailable rather than fabricated.

## Persistence and API

Migration 13 adds durable opportunity workflow fields: `brief_json`, `qualification_json`, `owner_gate_status`, `converted_project_id`, `converted_at`, and `last_action`, with an index for converted projects. Existing opportunity columns and APIs remain compatible. The following routes are live after the remote restart:

- `POST /v1/opportunities`
- `GET /v1/opportunities/{opportunity_id}`
- `POST /v1/opportunities/{opportunity_id}/analyze`
- `POST /v1/opportunities/{opportunity_id}/qualify`
- `POST /v1/opportunities/{opportunity_id}/convert`
- `POST /v1/opportunities/{opportunity_id}/start`

## Files changed in this phase

- `services/orchestrator/app/db.py` â€” schema version 13 and opportunity migration.
- `services/orchestrator/app/coordination/owner_control.py` â€” opportunity workflow fields, transitions, and updates.
- `services/orchestrator/app/organization/director.py` â€” SEO-aware role selection and execution dependencies.
- `services/orchestrator/app/organization/intake.py` â€” Sales-to-project orchestration service.
- `services/orchestrator/app/routers/incident_control.py` â€” opportunity intake and lifecycle API routes.
- `services/orchestrator/app/schemas.py` â€” lifecycle request models.
- `services/orchestrator/tests/test_sales_seo_workflow.py` â€” deterministic Sales/SEO integration and idempotency coverage.

Other files already modified by earlier phases were preserved; no unrelated changes were removed.

## Validation

| Check | Result |
|---|---|
| Orchestrator full suite | PASS â€” 243 passed, 1 skipped, 0 failed |
| Sales/SEO workflow suite | PASS â€” 8 passed |
| Dynamic execution-team regression suite | PASS â€” 9 passed (included in the full suite) |
| Model Gateway suite | PASS â€” 26 passed |
| Local Agent suite | PASS â€” 2 passed via `unittest` |
| Python compile check | PASS |
| `git diff --check` | PASS; only normal LF/CRLF warnings |
| Live Orchestrator health | PASS â€” HTTP 200; Model Gateway and Local Agent dependencies healthy |
| Live opportunity OpenAPI paths | PASS â€” all six lifecycle paths present |
| TypeScript/frontend checks | NOT_RUN â€” no frontend source changed in this phase |
| Optional real-model smoke | NOT_RUN â€” deterministic tests use controlled model boundaries |

## Security and operational notes

The implementation keeps commercial commitments behind the existing owner-control boundary, uses least-privilege role selection, preserves project isolation, and does not add credentials or remote push behavior. A verified timestamped remote backup was created before each edit batch; the latest pre-edit archive was `corrective-phase3-preedit-tar-20260919-125820.zip` with SHA256 `212925F6727109F713F624F3985DA20E1513E273CC5C90074BDC3A0C70B33B99`.

## Remaining limitations

External CRM/payment/contract integrations are intentionally not automated. SEO analytics and ranking data require an authorized data source. Human Owner approval remains required for unsupported fit and other commercial commitments. Frontend build/type checks were not applicable to the changed files.

# Corrective Phase 4 Technical Report â€” Deployment Safety and Release Cleanup

| Field | Value |
|---|---|
| Gregorian date | 2026-09-20 |
| Jalali date | 1405-06-29 |
| Scope | IIS exposure, control-plane authentication, gateway protection, autonomy/configuration safety, release packaging |
| Deployment performed | NO |
| Remote push performed | NO |

## Authentication boundary

`services/orchestrator/app/security.py` adds `ControlPlaneAuthMiddleware`. Health, readiness and documentation endpoints remain liveness-public. Other routes require `X-AI-Engine-Token` or `Authorization: Bearer`. High-risk route families (`/v1/developer`, `/v1/self-improvement`, `/v1/owner`, recovery run controls and agent project controls) additionally require `X-AI-Engine-Owner-Token`. Tokens are loaded through `SecretStr` settings and compared with `hmac.compare_digest`.

`services/model-gateway/app/security.py` adds `GatewayAuthMiddleware`; only liveness/documentation paths are public when `GATEWAY_AUTH_REQUIRED=true`. Orchestrator downstream requests propagate `MODEL_GATEWAY_TOKEN` only to the configured gateway URL.

## Privileged endpoint protection

The boundary is server-side and does not trust request fields such as `approved=true`. IIS remains a reverse proxy; `httpErrors existingResponse="PassThrough"` preserves 401/403 responses. The static frontend is not given privileged tokens. Production startup fails closed when required tokens are absent.

## Autonomy safety

Settings, `.env.example` and the Windows launcher default `AUTONOMOUS_MODE_ENABLED=false` and `AUTONOMOUS_AUTO_PUSH=false`. Explicit protected machine variables (`AI_ENGINE_AUTONOMOUS_MODE_ENABLED`, `AI_ENGINE_AUTONOMOUS_AUTO_PUSH`) are required to opt in. The current server `.env` is an existing opt-in runtime configuration (`AUTONOMOUS_MODE_ENABLED=true`, auto-push false) and is a pre-restart review blocker, not a source default.

## Configuration and documentation

Updated service environment examples, schema-version references (13), Electron architecture references, deployment instructions, authentication requirements, and the deployment rollback runbook. The server launcher resolves the project root from environment or script location and uses loopback service ports 8010/8011/8012.

## Release cleanup

`deploy/windows-server/package-release.ps1` creates a sanitized ZIP without `.git`, virtual environments, `node_modules`, caches, logs, runtime data, workspaces, backups, database copies, credentials, private keys or local `.env` files. Safe `.env.example` templates are retained. A server packaging smoke run produced a 6,790,985-byte archive; forbidden-entry and high-confidence content scan returned no matches and four safe `.env.example` files were present.

## Deployment health checks

The HTTPS probe to devoria.ir failed during connection setup. The current HTTP public proxy returned HTTP 200 for the existing unauthenticated gateway route because the running processes have not been restarted with the new boundary; both conditions are explicit release blockers.

## Rollback plan

Run the complete test/build gate, create and checksum a timestamped backup, configure protected tokens, restart, run authenticated health and smoke checks, and retain the backup. On failure stop the new instance, restore the verified checkout/data backup, restart the previous version and rerun health checks. No irreversible deployment was performed.

## Exact validation results

| Check | Result |
|---|---|
| Orchestrator full unittest discovery | PASS â€” 247 passed, 1 skipped, 0 failed |
| Orchestrator deployment security tests | PASS â€” 4 passed |
| Model Gateway full pytest suite | PASS â€” 27 passed, 0 failed |
| Model Gateway security test | PASS â€” 1 passed |
| Local Agent unittest discovery | PASS â€” 2 passed, 0 failed |
| SEO/company integration subset | PASS â€” 33 passed, 0 failed (included in Orchestrator total) |
| Python compileall | PASS |
| `git diff --check` | PASS (line-ending warnings only) |
| Control Center `npm run build` | PASS (tsc + Vite) |
| Desktop build/typecheck | NOT_RUN â€” dependencies absent |
| Sanitized package smoke test | PASS â€” 6,790,985 bytes; no forbidden entries |
| Loopback health identity checks | PASS â€” Gateway, Local Agent, Orchestrator HTTP 200 |
| Authenticated public health check | NOT_RUN â€” required machine tokens absent |

## Remaining server blockers

`READY_FOR_DEPLOYMENT = NO`. Exact blockers: (1) configure protected machine control-plane, owner and gateway tokens; (2) restart services so the new middleware is active; (3) change/review the existing runtime autonomy opt-in before public restart; (4) configure and verify HTTPS/IIS authenticated proxy behavior; (5) install Desktop dependencies if a Desktop build is a release requirement; (6) rerun authenticated health and smoke checks after restart.

### Health-script shape validation

The health script completed its response-shape and safety assertions with ephemeral non-secret test tokens against the reachable HTTP proxy. This validates the script logic only; real authenticated production validation remains NOT_RUN until machine tokens are configured and the services are restarted.
