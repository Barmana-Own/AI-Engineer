# Project Management and Multi-Project Scheduling

| Field | Value |
|---|---|
| Phase | 8C |
| Gregorian date | 2026-09-18 |
| Jalali date | 1405-06-27 |
| Status | Implemented in the existing coordination subsystem |

## Scope

Phase 8C adds project-management capabilities on top of the existing Supervisor, task DAG, message bus, handoff, memory, recovery and organization layers. It does not introduce another task or message store and does not change the desktop UI.

## Project lifecycle

ProjectPhase is persisted in projects.phase and every transition is recorded in project_lifecycle_events.

intake -> requirements -> architecture -> implementation -> integration -> testing -> review -> security_review -> release_verification -> completed

Operational branches are explicit: paused, failed, and cancelled can be entered only through the transition policy and can resume only through allowed transitions. Arbitrary jumps and completion without evidence are rejected.

The transition service validates quality gates:

- requirements must be passed before implementation;
- tests and review must be passed before release verification;
- `tests_passed` and `review_accepted` are mandatory before release verification; an optional `security_review` gate is enforced when present and may be waived only with explicit evidence;
- completion requires release evidence and all required gates passed or waived.

## Milestones, risks and deliverables

project_milestones stores durable deliverables, dependencies, due dates and state. project_risks stores severity, owner, mitigation and open/closed status. These records are project-scoped and are included in project synchronization output.

## Work queues and scheduler

agent_work_queue is the durable queue for tasks, reviews, questions, internal requests, meeting actions and blocked dependencies. Queue claims are transactional and ordered by priority and creation time; repeated claims return a conflict once an item is no longer queued.

POST /v1/scheduler/ready-tasks evaluates the existing coordination task DAG. A task is made ready only when every dependency is completed; independent tasks can be enqueued in parallel. The scheduler preserves the existing task state machine, skips writer tasks with active conflicting resource leases, and keeps lock acquisition transactional.

## Multi-project isolation

Every project has its own phase, gates, milestones, risks, task DAG, conversations, decisions, meetings, requests and project memory. Context-building and blackboard queries require a project scope when a project-specific view is requested. No project-specific row is copied into another project's state.

## Shared organizational blackboard

blackboard() derives a read model from authoritative tables. It exposes active projects, objectives, phases, open risks, blockers, decisions, failed tests, open reviews, pending questions and release status. It is not a chat transcript and is never used as an alternative source of truth.

## Resource safety

Task execution continues to use coordination_locks. A writable resource is held by one task at a time; read-only work can proceed when it does not conflict. The lock API is transactional and requires a persisted task identity.

## HTTP API

All routes are under /v1:

- GET /projects/{project_id}/management
- POST /projects/{project_id}/phase
- GET /projects/{project_id}/lifecycle
- GET|POST /projects/{project_id}/quality-gates
- GET|POST /projects/{project_id}/milestones
- GET|POST /projects/{project_id}/risks
- GET /work-queues
- POST /projects/{project_id}/work-queues
- POST /work-queues/{queue_id}/claim
- POST /work-queues/{queue_id}/complete
- POST /scheduler/ready-tasks
- GET /blackboard
- GET /projects/{project_id}/sync

## Database migration

Migration 9 is additive and idempotent. It adds lifecycle events, milestones, risks, quality gates and agent work queues. Existing project/task/message/memory data is retained. Schema initialization remains deterministic and isolated test databases are supported.

## Limitations

Scheduling remains in-process and SQLite-oriented. A distributed queue/lock service and measured cross-project resource capacity are not part of Phase 8C. The existing role worker adapter and JavaScript dependency gaps remain documented release work.


## Phase 8C implementation update

The Project Manager facade (`app/coordination/project_management.py`) now provides a stable delivery-coordination boundary for milestones, risks, lifecycle status, scheduling and reports without introducing a second task system. Project priority is applied before task priority when scheduling across projects. Writer tasks are held back when their declared resources conflict with active persisted coordination leases; read-only tasks remain eligible. The derived blackboard excludes paused and terminal projects from `active_projects` while retaining their authoritative lifecycle data in scoped views.

Migration 9 is verified as additive and idempotent for lifecycle events, milestones, risks, quality gates and durable agent work queues. The current orchestrator validation baseline is 114 passing tests with one documented skip. Phase 8D has not started.

### Review rejection behavior

Setting the `review_accepted` quality gate to `failed` while a project is in review, security review or release verification automatically reopens the `implementation` phase, preserves the failed gate evidence and records a lifecycle event. This keeps review rejection from silently allowing completion or leaving work without an actionable rework state.


The final Phase 8C project-management suite contains 10 passing tests, including the automatic review-rejection rework transition.
