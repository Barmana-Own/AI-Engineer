# AI-Engineer Organizational Core

| Field | Value |
|---|---|
| Scope | Phase 8A |
| Gregorian date | 2026-09-18 |
| Jalali date | 1405-06-27 |
| Implementation status | Implemented and covered by deterministic tests |

## Organizational architecture

The organizational layer sits above the existing coordination engine:

```text
Human Owner
    |
Company Director (executive, non-programming)
    |
Project / Engineering Management
    |
Existing Supervisor -> task DAG -> messages -> handoffs -> memory/recovery
    |
Persistent specialist employee profiles
```

The layer does not create another task, message or memory subsystem. It stores
organizational identity and project membership, then delegates technical work to the
existing `coordination.Supervisor`, scheduler, message bus, handoff protocol and
memory services.

## Company Director

`CompanyDirector` is an executive coordinator with read-only tools and a reasoning
model profile. It evaluates objective scope, forms a project organization, assigns
project and engineering leadership, monitors blocked/stalled team members, returns
executive reports and can issue a structured postmortem request. It never writes
source code or executes specialist tasks directly.

New project creation forms a small default team. Explicit planning through
`POST /v1/organization/projects/{project_id}/organize` can re-plan a project when
scope evidence justifies small, medium or large complexity.

## Persistent employee profiles

`agent_profiles` provides stable identities across runs. Profiles persist:

- agent ID, canonical role and display name
- department, capabilities and specializations
- allowed tools and write permission
- model profile and operational status
- active project and current task IDs
- validated experience summary and timestamps

Statuses are operational only: offline, idle, available, planning, working, waiting,
blocked, reviewing, meeting, paused and failed. No emotions, intelligence scores or
personality/loyalty fields are stored.

## Departments and roles

Departments are EXECUTIVE, PRODUCT, ENGINEERING, QUALITY, SECURITY, RESEARCH,
OPERATIONS and DOCUMENTATION. They are labels used for staffing and reporting; role
resolution remains owned by the canonical coordination role registry.

Phase 8A adds `company_director`, `project_manager`, `engineering_manager` and
`operations` contracts and aliases. Existing requirements, architect, researcher,
backend, frontend, implementer, integration, tester, debugger, reviewer, security,
docs and release_verifier contracts are reused.

## Dynamic team policy

| Complexity | Team |
|---|---|
| Small | Engineering Manager, Implementer, Tester, Reviewer |
| Medium | Engineering Manager, Architect, Implementer, Integration, Tester, Reviewer, Documentation |
| Large | Project Manager, Requirements, Engineering Manager, Architect, Backend, Frontend, Integration, Tester, Security, Documentation, Release Verifier |

The planner uses declared complexity first, then objective length, technologies,
skills, risks and deliverables as bounded evidence. It does not spawn every role for
every task. Profiles are reused by stable role-based IDs.

## Persistence and migration

SQLite schema version 7 is an additive migration. Existing projects and APIs remain
valid. Migration 7 adds project leadership, departments, phase, priority and team
state columns to `projects`, plus `agent_profiles` and
`project_team_members`. Initialization is deterministic and idempotent; legacy
databases retain their existing rows.

## APIs

- `GET /v1/organization/departments`
- `GET /v1/organization/employees`
- `GET /v1/organization/employees/{agent_id}`
- `POST /v1/organization/employees/{agent_id}/status`
- `POST /v1/organization/projects/{project_id}/organize`
- `GET /v1/organization/projects/{project_id}/team`
- `GET /v1/organization/projects/{project_id}/report`

## Validation

The Phase 8A suite covers profile persistence and restart reads, director profile
creation, department and role compatibility, deterministic small and large staffing,
project/team persistence, idempotent migration and bounded complexity inference.
The full Orchestrator suite remains the release gate; JavaScript dependency gaps and
the documented specialist worker adapter remain outside this phase.
