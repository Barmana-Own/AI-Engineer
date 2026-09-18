> **Implementation status (2026-09-18 / 1405-06-27):** This document describes the current coordination implementation. SQLite schema version is **6**. The Supervisor persists and coordinates the DAG, messages and handoffs; specialist model calls still run through the established agent execution loop rather than one OS worker per role. See `docs/final-engineering-review.md` for verified limits and test evidence.\n\n# Multi-Agent Coordination Engine

## Scope

Phase 2 adds a coordination layer to the existing FastAPI Orchestrator without merging the Local Agent, Model Gateway, or Desktop boundaries. The coordination layer owns role contracts, task dependencies, persisted agent communication, handoffs, bounded discussions, supervisor decisions, and workspace safety.

## Role registry

`services/orchestrator/app/coordination/roles.py` is the canonical registry. It defines contracts for `supervisor`, `requirements`, `planner`, `architect`, `researcher`, `backend`, `frontend`, `implementer`, `tester`, `debugger`, `reviewer`, `security`, `integration`, `docs`, and `release_verifier`. Each contract includes purpose, responsibilities, capabilities, allowed tools, write permission, model profile, input/output expectations, and escalation rules. Legacy aliases resolve to canonical IDs through `resolve_role`.

## Supervisor and task graph

`coordination/supervisor.py` creates a run and a dependency-aware engineering DAG:

1. requirements
2. planner
3. architect
4. backend, frontend, and implementer (independent scopes)
5. integration
6. tester
7. reviewer
8. release verifier

`coordination/scheduler.py` moves tasks through `pending`, `ready`, `assigned`, `running`, `waiting`, `blocked`, `review`, `failed`, `completed`, and `cancelled`. A task is not ready until every dependency is completed. Failed dependencies block downstream work. Retry counts and maximum retries are persisted.

## Message and discussion protocol

`coordination/bus.py` persists typed messages in `agent_messages`. Supported types are `QUESTION`, `ANSWER`, `PROPOSAL`, `EVIDENCE`, `REVIEW`, `CHALLENGE`, `REVISION_REQUEST`, `DECISION`, `HANDOFF`, `BLOCKER`, `STATUS`, and `RESULT`. Messages are filtered by run, project, and task instead of concatenating unrelated history. `DiscussionController` applies a maximum round limit and requires Supervisor resolution after the limit is reached.

## Handoffs and context

`HandoffProtocol` persists completed work, artifacts, changed files, decisions, risks, remaining work, and verification evidence in `coordination_handoffs`. `ContextBuilder` assembles bounded context from the current task, dependency summaries, relevant messages, recent handoffs, validated memory, and the role contract. It truncates oversized context rather than sending the entire database history to an agent.

## Concurrency and workspace safety

Read-only tasks can be grouped into parallel batches when scopes do not overlap. Writer tasks are serialized and acquire rows in `coordination_locks` for each declared resource. Lock acquisition is transactional and rejects a conflicting owner. The existing Local Agent remains the only component that performs filesystem, terminal, and Git operations; coordination writer permissions are orchestration policy, not a bypass around Local Agent controls.

## Persistence and migration

Database schema version 6 adds `coordination_tasks`, `coordination_task_dependencies`, `agent_messages`, `coordination_handoffs`, and `coordination_locks`, with foreign keys and indexes. Initialization is deterministic and idempotent through the existing migration runner. Existing projects, tasks, memories, autonomy runs, and subagent handoffs remain intact.

## API surface

The additive `/v1/coordination` router exposes role contracts, run creation/status, task and dependency inspection, messages, handoffs, agent status aggregation, and task result/failure/revision callbacks. Existing routes remain unchanged.

## Validation

The deterministic coordination suite covers role aliases, dependency gating, read-only batching, writer lock exclusion, message and handoff persistence, bounded discussion, Supervisor delegation/completion, and failure/retry behavior. Model execution is intentionally left behind the existing Model Gateway and Local Agent boundaries; the current Supervisor creates and tracks work but does not replace the existing agent execution loop.

## Known limitations

- Agent model invocation and filesystem execution still occur through the existing worker services; a future phase may connect each DAG task to a dedicated worker queue.
- API authentication/authorization continues to follow the existing Orchestrator policy and should be extended before exposing coordination mutation endpoints outside a trusted control plane.
- Writer leases have bounded expiry and stale locks can be reclaimed transactionally; long-running workers should reacquire before expiry because no background heartbeat is provided.


