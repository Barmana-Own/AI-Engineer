# Phase 8E — AI Company Integration Validation

| Field | Value |
|---|---|
| Project | AI-Engineer |
| Phase | 8E — Full AI Software Company Integration Validation |
| Gregorian date | 2026-09-18 |
| Jalali date | 1405-06-27 |
| Repository revision | `dc436aa` (validation baseline; working tree contains prior phase changes) |
| Status | PASS for the exercised deterministic integration scope |

## Final AI company architecture

The existing Orchestrator, Model Gateway, Local Agent, persistence, task DAG, message bus, handoff, memory, recovery, incident and owner-control layers remain separate. Phase 8E adds a thin persisted company trace layer on top of those boundaries. `company_events` is a local SQLite event ledger; it is not a second workflow engine and does not replace authoritative task, message, handoff, meeting, project, incident or memory stores.

## Organizational hierarchy and roles

The simulation uses Human Owner, Company Director, Project Manager, Engineering Manager, Requirements, Architect, Security, Backend, Frontend, Integration, Tester, Debugger, Reviewer, Documentation, Release Verifier and Incident/Ops roles. Team creation is delegated to the existing Company Director and persistent employee profile/department model. Technical execution remains delegated to specialized agents.

## Simulated company run

`CompanySimulation` creates a large project for the objective “Build a small full-stack application with authentication, API, frontend, tests and documentation.” It invokes the existing real `EngineeringDemoRunner`, then persists company-level evidence for:

- project/team creation and agent assignments;
- a task DAG and delegated task assignments;
- proposal, security challenge, evidence and counter-proposal messages;
- Engineering Manager decision resolution;
- kickoff meeting, meeting decision and action item;
- Frontend → Backend API clarification request and response;
- Architect → Engineering Manager handoff;
- test failure → incident → debugger/engineer repair → tester verification;
- reviewer rejection/revision evidence from the engineering trace;
- security review, documentation and release-verification gates;
- validated postmortem lesson and final Company Director completion event.

The run writes JSON and Markdown trace artifacts under the requested output directory. `GET /v1/company/projects/{project_id}/trace` and `/trace/markdown` expose the same persisted evidence for future dashboards; `GET /v1/company/events` provides bounded event queries.

## Restart and multi-project evidence

The simulation runs the existing restart-aware engineering demo. The integration test rebuilds the trace after database initialization and verifies event/task counts and the persisted recovery event without duplicating completed tasks. Event queries are project-scoped and `INSERT OR IGNORE` makes a supplied event ID idempotent. The isolation test creates two projects and verifies that events for one project are not visible in the other. The existing project-management suite additionally covers separate DAGs, project memory/context isolation, priority scheduling and writer-resource conflicts.

## Database migration

Schema version 11 adds `company_events` with project/run/task foreign-key references, actor fields, redacted JSON payload, timestamp and indexes for project/run/type timelines. Initialization is deterministic and idempotent; older databases are upgraded through the existing migration chain without removing data.

## Validation evidence

| Suite | Result |
|---|---|
| Orchestrator (including Phase 8E) | 120 passed, 1 skipped (optional real-model smoke) |
| Model Gateway | 26 passed |
| Local Agent | 2 passed |
| Changed-module compile check | PASS (`db.py`, `company_trace.py`, router, `main.py`) |
| API route registration | PASS; company trace endpoints present |

## Known limitations and technical debt

- The simulation is a deterministic integration fixture. Model calls remain at the existing mocked/boundary level; it is not a claim of autonomous production deployment.
- The company event ledger is local SQLite and intentionally does not provide distributed event streaming or cross-host ordering guarantees.
- Existing engineering-demo traces remain authoritative for detailed tool/test/review evidence; the company ledger summarizes cross-organizational milestones.
- Real frontend/backend artifact generation, remote publication and production deployment still require an explicitly authorized project run and environment.

## Files added or changed in Phase 8E

- `services/orchestrator/app/db.py` — schema version 11 and `company_events` migration.
- `services/orchestrator/app/coordination/company_trace.py` — persisted events, trace assembly/rendering, deterministic company simulation.
- `services/orchestrator/app/routers/company_trace.py` — event and trace APIs.
- `services/orchestrator/app/main.py` — router registration.
- `services/orchestrator/tests/test_company_trace.py` — end-to-end persisted simulation and project-isolation/idempotency tests.
