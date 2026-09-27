# Phase 8D - Incident Management, Organizational Learning and Human Owner Control

## Scope

Phase 8D adds an organizational resilience layer on top of the existing Orchestrator coordination engine. It does not replace the task DAG, message bus, handoff persistence, memory store, project manager or recovery system.

The implementation preserves the existing Electron Desktop / React Control Center ? FastAPI Orchestrator ? Model Gateway and Local Agent boundaries.

## Incident system

Incidents are persisted in SQLite and move through an explicit state machine:

`detect ? contain ? diagnose ? repair ? verify ? postmortem ? learn ? resolved`

Only the next valid phase is accepted. A transition is idempotent when the requested phase is already current, and every accepted transition creates an `incident_events` record with actor, details and evidence. Incident severity is constrained to `critical`, `high`, `medium` or `low`.

`assign_incident_team` creates durable team membership for an Incident Manager, Debugger, Tester, Operations, Security and relevant Engineer. Existing employee profiles are reused. Missing profiles are created through the organization store. Team selection uses measured performance rows from `agent_performance`; it does not create intelligence or personality scores.

## Postmortems and organizational memory

A postmortem records impact, timeline, root cause, contributing factors, repair, verification, prevention ideas and follow-up tasks. One postmortem is associated with each incident. A postmortem lesson is written to the existing `MemoryStore` as an organization-level lesson and is promoted only with evidence. Secret-like content is sanitized by the existing memory sanitizer. No raw incident narrative is automatically trusted.

Organizational lesson retrieval is scoped to `project_id IS NULL` and uses the existing ranked memory retrieval. Project lessons remain project-scoped.

## Performance and collaboration learning

`agent_performance` remains the source of measurable role/model evidence: attempts, completed tasks, review rejections, test failures, retries, duration and successful domains. Team selection uses completion, failure and success-rate evidence for the requested role/domain.

`collaboration_quality` aggregates recurring engineering coordination problems by project and signature. It records occurrence count, severity, bounded examples and timestamps. It is intended for planning and postmortem review, not social or popularity scoring.

## Human Owner control

The Human Owner is above the Company Director and all specialized agents. Normal owner actions are persisted and applied through the existing project lifecycle service:

- `start_project`
- `pause_project`
- `resume_project`
- `cancel_project`
- `change_priority`
- `request_report`
- `approve_major_decision`
- `reject_major_decision`
- `request_review`

High-risk operations are represented but never executed automatically: production deployment, remote publication, destructive infrastructure changes, credential-sensitive operations, external commitments and financial commitments. They remain `pending_approval` until the Human Owner resolves the action. Approval records an explicit external-operator requirement; it does not invoke a deployment, payment or remote publication.

Payloads and reasons pass through the existing memory redaction/sanitization boundary. Non-owner actors are rejected by the service layer.

## External intake abstraction

The `ProjectOpportunity`, `ClientMessage`, `ProjectProposal`, `ClientRequirement` and `ClientApproval` dataclasses define an adapter-neutral boundary. `project_opportunities` stores source, optional external reference, title, summary, requirements and inbox status. No Upwork, Fiverr or other platform adapter is implemented in this phase.

## Persistence and migration

Schema version 10 adds:

- `incidents`, `incident_events`, `incident_team_members`
- `postmortems`
- `collaboration_quality`
- `owner_control_actions`
- `project_opportunities`

Migration 10 is additive and idempotent. Existing project, task, memory, run, handoff and employee data is preserved. Foreign keys and indexes cover project/run, incident timeline, team membership, postmortem lookup, pending owner actions and opportunity status. Test databases use isolated temporary SQLite files.

## API surface

The router `app.routers.incident_control` exposes the `/v1` endpoints for incident creation/transitions/events/team, postmortems/lessons, organizational lessons/performance/team selection, collaboration quality, Human Owner actions/resolution and opportunity intake. Existing routes remain unchanged.

## Validation

- Orchestrator: 118 passed, 1 skipped (the optional real-model smoke test).
- Phase 8D targeted tests: 4 passed.
- Model Gateway: 26 passed (`pytest`).
- Local Agent: 2 passed (`unittest`).
- Changed Python modules compile successfully.
- FastAPI import smoke: 125 routes loaded, including 8 incident routes.

## Limitations and safety boundaries

Authentication/authorization for the HTTP control plane remains the responsibility of the existing deployment boundary; the owner-control service enforces the `human_owner` actor contract but does not invent a new identity provider. Incident teams are role/profile assignments, not separate worker processes. SQLite remains appropriate for the current single-process coordination model; distributed incident queues and cross-host locks are not introduced. External opportunity adapters, automatic production deployment, financial actions and remote publication remain intentionally unimplemented.
