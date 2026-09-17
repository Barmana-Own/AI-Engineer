# AI-Engineer Technical Audit Report

| Field | Value |
|---|---|
| Project | AI-Engineer |
| Report type | Technical engineering handoff |
| Language | English |
| Jalali date | 1405-06-27 |
| Gregorian date | 2026-09-18 |
| Repository snapshot | main; audit observed recovery commit fd80c52 and one local commit ahead of origin |
| Audit scope | Source tree, tests, SQLite snapshot, deployment scripts, and local service probes |

## Scope and evidence

This report records a source-first audit of the current checkout. The audit itself made no major application-source modification. It created the implementation plan and refreshed the bilingual audit reports. During the audit, the already-running supervisor created a recovery checkpoint commit that changed README.md; it was not reverted.

## Current architecture

The verified boundary is:

UI/Desktop  Orchestrator  Local Agent (workspace/files/Git/terminal/processes)
 Model Gateway (provider/model routing)

The Orchestrator owns task scheduling, autonomy runs, role execution, memory, handoff persistence, and health/developer routes. The Local Agent exposes guarded machine operations. The Model Gateway fronts provider adapters and readiness checks. The React Control Center consumes typed Orchestrator endpoints. The Desktop implementation is Electron in source, while portions of the documentation still describe a future Tauri/Rust stack.

## Current agent workflow

The current loop selects one target from a fixed 14-item autonomous backlog, creates a bounded goal and validation command, then runs specialist phases. Read-only specialists may run in bounded parallel batches; writer roles are isolated and executed serially. Successful mutation work is checkpointed only when validation permits it. Handoffs are persisted as structured records and memories are compacted from terminal outcomes. A five-minute scheduler skips active runs and reconciles stale work.

This is useful bounded automation, but it is not yet a project-level supervisor workflow: there is no durable project intake, requirement baseline, dependency-aware task DAG, work lease protocol, explicit acceptance gate, or terminal release decision.

## Existing roles and contracts

The registry contains inspector, planner, implementer, verifier, reviewer, monitor/Supervisor Manager, requirements, architect, orchestrator, gateway, local-agent, UI, desktop, tests, security, docs, debugger, and integration roles, with aliases for scout/local-agent/test-verifier/manager. Role metadata distinguishes read-only and writer/validation behavior. The contract is primarily prompt and handoff metadata; it does not yet enforce organization-wide inbox, challenge, question, revision, or decision semantics.

## Persistence model

SQLite uses WAL, foreign keys, and a busy timeout. Current tables are projects, agent_tasks, agent_memories, autonomy_runs, and subagent_handoffs, with status/project indexes. Persistence records task outcomes, validation commands, changed paths, bounded terminal detail, memories, and handoffs. Missing primitives include message/event tables, task dependencies, leases/locks, durable decisions, acceptance evidence, and resumable workflow state.

The current snapshot contained 1 project, 1,110 tasks, 1,110 memories, 498 autonomy runs, and 1,110 handoffs. Run outcomes were 335 completed and 163 failed; handoffs were 947 completed, 157 failed, and 6 running. The observed data range was 2026-09-15T08:35:40Z through 2026-09-17T20:57:43Z.

## Main technical debt and risk

- agent_service.py is 3,270 lines and mixes tool policy, mutation safety, model actions, execution, recovery, and orchestration.
- autonomy.py is 944 lines and owns backlog selection, scheduling, retries, reconciliation, and checkpoint push.
- No authentication middleware or authorization model exists on Orchestrator routes.
- CORS allows all methods/headers for loopback origins; task request extras are accepted.
- Deployment defaults set AUTONOMOUS_AUTO_PUSH=true; the push path stages and commits to origin main.
- Desktop electron/main.cjs hard-codes F:\AI-Engineer.
- Provider Router and Desktop dependency trees are absent in the checkout; their runnable checks cannot currently complete.
- Documentation and historical reports contain stale stage/status claims and Tauri references.
- Failure records include 360-second timeouts, max-step exhaustion, restart reconciliation, and invalid/unsupported model-tool actions.

## Communication capability gap

Current handoffs are append-only structured summaries with evidence, changed files, validations, blockers, confidence, and previous handoff IDs. There is no mailbox/message entity, addressed question, challenge/rebuttal, supervisor decision, revision request, acknowledgement, or durable event stream. Parallel phases are bounded, but write contention is prevented mainly by phase isolation rather than task-scoped leases.

## Test baseline and service probes

| Check | Result |
|---|---|
| Orchestrator unittest discovery | PASS  62 |
| Local Agent unittest discovery | PASS  2 |
| Model Gateway pytest | PASS  26 |
| Python compileall | PASS  all three services |
| Control Center npm build | PASS |
| Desktop npm build | NOT_RUN/blocked  Vite executable/dependencies missing |
| Provider Router npm test | NOT_RUN/blocked  Vitest executable/dependencies missing |
| Orchestrator 8012 health/capabilities | PASS |
| Local Agent 8011 health | PASS |
| Model Gateway 8010 health/readiness | PASS |
| Provider Router 8020 | NOT_RUN  connection refused |
| Full lint/type/security audits and browser E2E | NOT_RUN |

Historical reports claiming different test totals or Desktop success were not used as current evidence.

## Proposed target architecture

Preserve the existing service boundaries and add modular Orchestrator capabilities:

1. Project intake and requirements baseline.
2. Supervisor control plane with role assignment, policy, decision log, and acceptance gates.
3. Durable workflow/task DAG with dependencies, priorities, retries, leases, and resumable checkpoints.
4. Message/event subsystem supporting assignment, question, challenge, evidence, revision, acknowledgement, and supervisor decisions.
5. Specialist execution adapters that continue to use Local Agent and Model Gateway through public interfaces.
6. Integration/review/release pipeline with required test, security, documentation, and verification evidence.
7. Authenticated, authorized API and operational observability.
8. Safe Git policy with checkpoint-only local commits by default and explicit release push authorization.

## Proposed implementation phases

| Phase | Primary outcome |
|---|---|
| 0 | Baseline, integrity manifest, and safety flags; disable auto-push default |
| 1 | Split agent service into policy/tool/execution/recovery modules without changing contracts |
| 2 | Add durable task DAG, dependencies, leases, idempotency, and resume state |
| 3 | Add inter-agent mailbox, questions/challenges, evidence, revisions, and supervisor decisions |
| 4 | Implement supervisor project intake, role assignment, scheduling, and acceptance gates |
| 5 | Add authentication, authorization, audit events, and security regression coverage |
| 6 | Integrate frontend/desktop observability and replace hard-coded paths/config drift |
| 7 | Complete integration, release verification, deployment hardening, docs, and full QA |

The exact file-level change set is recorded in docs/implementation-plan-autonomous-multi-agent.md; it includes focused additions under services/orchestrator/app (workflow, messaging, supervisor, policy, leases, acceptance, auth), schema and migration updates, targeted agent_service extraction, deployment configuration, and tests.

## Validation and release assessment

The core Python services and Control Center build are currently verifiable. Desktop and Provider Router checks are blocked by missing dependencies; lint, full security audit, and browser E2E were not run. No production release gate can pass until authentication/authorization, auto-push policy, workflow completion criteria, dependency installation, and the missing supervisor communication primitives are implemented and validated.