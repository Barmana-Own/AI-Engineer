# Current Architecture (Verified 2026-09-18 / 1405-06-27)

> This document is the current implementation reference. Earlier Tauri/Rust diagrams are obsolete: the desktop application in the source tree is Electron.

## Boundary map

```text
React Control Center / Electron Desktop
                 |
                 v
FastAPI Orchestrator
  coordination | persistence | recovery | public APIs
        |                         |
        v                         v
Model Gateway                 Local Agent
  profiles, routing,          files, Git, terminal,
  usage, cache, health        processes, health
        |
        v
Provider Router (optional provider integration)
```

The repository is a modular monolith at the orchestration layer, with separate processes for model access and local workspace tools. UI and Desktop clients call the Orchestrator; they do not own agent execution or database writes.

## Components

- **Orchestrator** (`services/orchestrator/app`): FastAPI routes, SQLite schema/migrations, agent execution loop, coordination store and scheduler, Supervisor, message bus, handoffs, memory/experience, self-improvement and restart recovery.
- **Model Gateway** (`services/model-gateway/app`): provider-neutral model profiles, provider selection, health, usage and cache boundaries.
- **Local Agent** (`services/local-agent/app`): constrained file, terminal, process and Git operations exposed to the Orchestrator.
- **Provider Router** (`services/provider-router/server`): optional provider-facing bridge. Its vendored/provider code is intentionally outside this review scope.
- **Control Center** (`apps/control-center`): React/Vite client.
- **Desktop** (`apps/desktop`): Electron shell with `contextIsolation`, disabled Node integration and sandboxing.

`services/memory-service`, `packages/agent-sdk`, `packages/tool-sdk`, `apps/web-ui` and `apps/vscode-extension` contain placeholders only; they are not active implementations.

## Agent coordination

The canonical role registry contains supervisor, requirements, planner, architect, researcher, backend, frontend, implementer, tester, debugger, reviewer, security, integration, docs and release_verifier roles plus compatibility aliases. Each contract declares capabilities, tools, write permission, model profile, input/output contract and escalation rules.

`Supervisor.start_objective` persists an autonomy run and a dependency-aware task DAG. The current fixed graph is requirements -> planner -> architect -> independent implementation tasks -> integration -> tester -> reviewer -> release verification. `DependencyScheduler` gates task readiness, batches independent read-only tasks and uses transactional workspace locks for writers. `CoordinationTask` states are pending, ready, assigned, running, waiting, blocked, review, failed, completed and cancelled.

The Supervisor coordinates evidence, decisions, retries, revisions, handoffs and final status. It does not replace the existing execution loop with a dedicated OS process per role; specialist model calls still occur through the established agent service/autonomy loop.

## Communication and handoffs

`MessageBus` persists typed messages: QUESTION, ANSWER, PROPOSAL, EVIDENCE, REVIEW, CHALLENGE, REVISION_REQUEST, DECISION, HANDOFF, BLOCKER, STATUS and RESULT. Each record is linked to project/run/task and sender/recipient roles. `HandoffProtocol` persists completed work, artifacts, changed files, decisions, risks, remaining work and verification. The discussion controller limits rounds and timeout, but its confidence field is currently advisory.

## Persistence and migrations

`services/orchestrator/app/db.py` runs deterministic, additive SQLite migrations with schema version tracking. Version 6 covers projects, agent_tasks, agent_memories, autonomy_runs, subagent_handoffs, coordination tasks/dependencies, agent messages, coordination handoffs/locks, experience memories/outcomes, failure patterns, agent performance, improvement candidates/cycles, execution leases, recovery events and provider failures. WAL mode and isolated temporary test databases are used. Existing databases are upgraded without destructive reset; newer unsupported versions fail fast.

## Memory and learning

Working, episodic, project, lesson and failure memory use candidate -> validated -> trusted -> superseded/rejected lifecycle. Promotion requires evidence; retrieval is scoped by project, role, task type, files and lexical relevance. Feedback updates measurable usefulness/confidence. Sanitization removes credential-like content. This is experience retention and routing/context improvement, not model retraining.

## Controlled self-improvement

The persisted lifecycle is OBSERVE -> DIAGNOSE -> PROPOSE -> PLAN -> CHECKPOINT -> IMPLEMENT -> TEST -> REVIEW -> ACCEPT/REJECT -> LEARN. Evidence comes from failed tasks/runs, retries and bounded TODO/FIXME inspection. Candidate prioritization penalizes recent failures. Limits cover changes, files, retries, runtime, roots and commands. Checkpoints are local; automatic remote push is disabled.

## Recovery

Startup initializes migrations and classifies incomplete work as safe_to_resume, needs_verification, waiting_for_dependency, waiting_for_approval, orphaned or terminal. Execution leases expire stale workers, heartbeat/release endpoints update ownership and recovery events are idempotent. Running work is never silently marked successful; verification is required after interruption. SQLite recovery is single-process oriented.

## Runtime configuration

`AI_ENGINE_PROJECT_ROOT` has priority, then `PROJECT_ROOT`, then runtime discovery, with a safe fallback. Launcher ports are Gateway 8010, Local Agent 8011, Orchestrator 8012 and Control Center 5175. Autonomous mode, improvement and remote push are opt-in/disabled by default. See `docs/configuration.md`.

## Historical documentation

`docs/roadmap.md` is the maintained roadmap. Any older document or archived diagram mentioning Tauri is historical and must not be used to infer the current runtime. `docs/implementation-plan-autonomous-multi-agent.md` is a plan/audit reference; source code and this document are authoritative for implementation status.
