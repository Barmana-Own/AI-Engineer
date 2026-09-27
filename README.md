# AI-Engineer

Production-oriented autonomous engineering workspace built as a modular monolith with explicit service boundaries.

## Current architecture

```text
React Control Center / Electron Desktop
                 |
                 v
FastAPI Orchestrator (coordination, persistence, recovery, APIs)
        |                         |
        v                         v
Model Gateway                 Local Agent
(model/provider routing)      (files, git, terminal, processes)
        |
        v
Provider Router (optional provider integration)
```

The source of truth is the implementation under `services/` and `apps/`. The desktop application is Electron (`apps/desktop`), not Tauri. The React Control Center is under `apps/control-center`.

## Services

- `services/orchestrator`: FastAPI API, SQLite persistence (schema version 13), coordination task DAG, message bus, handoffs, memory, self-improvement, recovery and run observability.
- `services/model-gateway`: model profiles, provider routing, caching, usage and health APIs.
- `services/local-agent`: constrained file, terminal, process and Git tools.
- `services/provider-router`: optional provider-facing integration; its own dependencies are required for its test command.

The placeholder packages `services/memory-service`, `packages/agent-sdk`, `packages/tool-sdk`, `apps/web-ui`, and `apps/vscode-extension` are not production implementations.

## Configuration and startup

Project-root discovery is portable. Set `AI_ENGINE_PROJECT_ROOT` (or the backward-compatible `PROJECT_ROOT`) when launching from another directory; otherwise the launcher discovers a parent containing `services` and `apps`.

```powershell
$env:AI_ENGINE_PROJECT_ROOT = (Get-Location).Path
.\start-ai-engineer.ps1
```

The launcher starts Model Gateway on 8010, Local Agent on 8011, Orchestrator on 8012 and the Control Center on 5175. Public deployment keeps autonomous execution and autonomous improvement disabled by default, requires control-plane/gateway tokens in the machine environment, and keeps `AUTONOMOUS_AUTO_PUSH=false`. The IIS site may serve the static frontend, but privileged `/api/orchestrator/*` and `/api/gateway/*` calls require authentication.

## Multi-agent execution

`Supervisor.start_objective` creates a persisted run and dependency-aware DAG: requirements, planner, architect, independent implementation work, integration, testing, review and release verification. `MessageBus` persists typed messages (question, proposal, evidence, review, challenge, revision request, decision, handoff, blocker, status and result). `HandoffProtocol` records structured artifacts and verification. The scheduler batches independent read-only work and serializes writers with transactional workspace locks.

The Supervisor currently owns orchestration and evidence; specialist model execution remains in the existing agent execution loop rather than a separate worker process per role. This is deliberate and documented as remaining debt, not a claimed feature.

## Organizational layer

The Company Director is the non-programming executive coordinator above the existing
Supervisor. Persistent employee profiles (agent_profiles) use stable role identities,
measurable capabilities, model profiles, tool permissions and operational statuses.
Departments are EXECUTIVE, PRODUCT, ENGINEERING, QUALITY, SECURITY, RESEARCH,
OPERATIONS and DOCUMENTATION.

Creating a project forms the smallest useful team by default. Small projects use an
Engineering Manager, Implementer, Tester and Reviewer; medium and large projects add
only the planning, architecture, integration, security, documentation and release
roles justified by scope. The existing coordination task DAG, message bus, handoffs,
memory and recovery tables remain the execution primitives. Organization APIs are
available under /v1/organization for employee profiles, team formation and executive
project reports. See docs/organizational-core.md.

## Memory and improvement

Working, episodic, project, lesson and failure memories use candidate/validated/trusted/superseded/rejected lifecycle states. Retrieval is scoped and lexical/ranked; secrets are redacted. Self-improvement follows observe, diagnose, propose, plan, checkpoint, implement, test, review, accept/reject and learn gates with bounded retries, file/change/runtime limits and local checkpoints.

## Validation

From the service directories:

```powershell
cd services/orchestrator; .venv\Scripts\python.exe -m unittest discover -s tests -v
cd ..\model-gateway; .venv\Scripts\python.exe -m pytest -q
cd ..\local-agent; .venv\Scripts\python.exe -m unittest discover -s tests -v
cd ..\..\apps\control-center; npm run build
```

The end-to-end deterministic workflow is covered by `services/orchestrator/tests/test_e2e_workflow.py`; its persisted trace is exposed at `GET /v1/coordination/runs/{run_id}/trace`.

## Known limitations

- Desktop and Provider Router JavaScript validation require their local Node dependencies; in the audited environment `vite`/`vitest` were not installed for those packages.
- The Local Agent package has unittest coverage; a separate pytest command is not available in its environment.
- SQLite persistence is designed for a single orchestrator process. The scheduler, discussion controller and specialist-worker execution still have documented edge cases; see `docs/final-engineering-review.md`.

For the verified architecture and release assessment, read `docs/final-engineering-review.md`.

## Incident resilience and Human Owner control

Phase 8D adds a persisted incident state machine (`detect -> contain -> diagnose -> repair -> verify -> postmortem -> learn -> resolved`), dynamic incident teams, postmortems, evidence-gated organizational lessons, measurable collaboration/performance signals and adapter-neutral opportunity intake. The Human Owner remains above the Company Director: normal project actions are persisted and high-risk operations stay pending approval with no automatic deployment, remote publication or financial execution. See `docs/incident-management.md` and the Phase 8D addenda in `reports/`.
