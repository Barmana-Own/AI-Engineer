# Phase 10B — Role-to-Skill Routing Report

| Field | Value |
| --- | --- |
| Project | AI-Engineer |
| Phase | 10B — Role-to-Skill Routing |
| Language | English |
| Jalali date | 1405-06-31 |
| Gregorian date | 2026-09-22 |
| Status | PASS |

## Skill Registry

The Phase 10A registry remains authoritative for the twelve imported playbooks. `skills/software-delivery/role-skill-map.json` is the single registry-backed role policy consumed by `services/orchestrator/app/skill_routing.py`. Unknown skill IDs fail closed and external `allow_implicit_invocation` metadata cannot activate a skill.

## Role-Skill Matrix

The routing policy covers requirements, project management, UX, architect, backend, frontend, implementer, integration, security, tester, debugger, DevOps, reviewer, release verifier, engineering manager, documentation, SEO, and Sales compatibility. Conditional rules prevent UI, database, security, and deployment skills from being selected without evidence from the task/project context.

## Skill Router

`SkillRouter` accepts project type, objective, requirements, risk, technologies, phase, assigned role, and optional project-selected skills. It returns bounded selections containing skill ID, reason, priority, required/optional mode, and matched condition. `route_project` derives a contextual project set without imposing a mandatory twelve-stage pipeline.

## Dynamic Stage Adaptation

Stage dependencies are derived only for selected skills. A documentation-only task selects no engineering stages. Backend-only work can flow through backend/database/testing/QA/final review without UI stages. Full-stack work activates relevant UI, frontend, backend, API, auth/security, testing/QA, deployment (when requested), and final-review stages.

## Context Loading Design

`SkillContextLoader` loads only selected `SKILL.md` documents and explicitly requested declared references. It requires task, role, and project scope, enforces byte/reference limits, and does not execute scripts or create state. Scripts remain behind Agent Worker → Tool Policy → Local Agent.

## Quality Gate Integration

Structured skill evidence is supported for artifacts, checks, findings, gate status, handoff, and evidence. Required gates reject missing objective evidence. Testing requires passed tests and checks; QA requires regression evidence; security requires resolved findings; deployment requires health checks; final review requires acceptance, no critical findings, and checks.

## Permission Model

Effective tools are the intersection of role permissions, task permissions, selected skill requirements, and global policy. A playbook cannot grant a tool that the role/task/global policy does not already allow. The full-stack review metadata now explicitly includes read-only `diff` inspection, which remains constrained by the intersection.

## Persistence

The existing `agent_tasks` table now persists `skill_selections_json` and `skill_trace_json` with idempotent startup migration. `db.set_task_skill_route` records route decisions on the existing task record; task API responses expose `skill_selections` and `skill_trace`. Existing task callers remain compatible.

## Test Results

| Validation | Result |
| --- | --- |
| Targeted role-to-skill/context/gate/persistence tests | 16 passed |
| Full orchestrator suite | 73 passed, 10 subtests passed |
| Phase 10A registry/state regression tests | 9 passed |
| Changed Python syntax compilation | PASS |
| Live worker connection/global stage enforcement | NOT RUN — explicitly out of scope for Phase 10B |

## Limitations

This phase provides routing, bounded context selection, evidence contracts, quality-gate evaluation, and task persistence. It does not connect skills to the live Agent Worker runtime and does not turn the imported sequential stage descriptions into a global workflow.