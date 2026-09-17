# AI Engineer  Fresh Technical Audit and Autonomous Multi-Agent Implementation Plan

| Field | Value |
|---|---|
| Repository | AI Engineer |
| Audit scope | Existing source tree on the Windows Server checkout |
| Audit date (Gregorian) | 17 September 2026 (server checkout timestamp) |
| Audit basis | Source inspection, SQLite read-only queries, service health probes, unit/pytest/build commands |
| Change policy | Audit and plan only; no production source code or configuration changed |
| Git state at audit start | main...origin/main, clean working tree |

## Executive summary

The repository already contains a functioning local-first execution core. The architectural boundary is sound and must be retained:

Control Center / Electron Desktop
              |
         Orchestrator
        /             \
 Local Agent      Model Gateway
 (OS boundary)    (model routing)
              |
        SQLite persistence

The orchestrator currently executes guarded single-agent tasks and a scheduled bounded supervisor loop. The role registry names most of the requested specialists, and persisted handoffs provide a useful evidence record. The system is not yet an autonomous engineering organization: there is no durable work DAG, typed mailbox/question/review protocol, supervisor decision record, project-intake pipeline, robust resume/idempotency contract, or release-quality end-to-end validation.

The latest database snapshot contains 498 autonomy runs (335 completed, 163 failed), 1,110 tasks, 1,110 memories, and 1,110 handoffs. Only 30 memories record a changed path and every one points to README.md; the loop is therefore producing mostly no-op or recovery activity rather than substantive product evolution. The latest failures are dominated by autonomous timeouts, maximum-step exhaustion, restart reconciliation, and invalid model tool-call output.

The immediate engineering objective is to stabilize the execution contract, then add coordination primitives incrementally while preserving the existing service boundaries and single-writer safety model. Automatic remote pushing must remain disabled during this work; the deployment script currently sets AUTONOMOUS_AUTO_PUSH=true and is a release-safety risk.

## 1. Current architecture

### Runtime components

| Layer | Current implementation | Evidence / notes |
|---|---|---|
| Operator UI | apps/control-center React/Vite control center; apps/desktop Electron shell | Control Center build passes. Desktop source is Electron (electron/main.cjs), while older documentation still describes Tauri. |
| Orchestration | services/orchestrator/app/main.py, routers, agent_service.py, autonomy.py, subagents.py | FastAPI service on port 8012; project/task/autonomy/memory/handoff APIs. |
| OS execution boundary | services/local-agent | FastAPI service on port 8011; guarded files, terminal, process, Git and environment operations. |
| Model routing | services/model-gateway | FastAPI service on port 8010; provider abstractions, retries/fallbacks, runtime model and usage endpoints. |
| Provider Router | services/provider-router | Node/SQLite OpenAI-compatible service kept as a separate integration; do not modify vendored code without a failing contract that cannot be solved at the public interface. |
| Persistence | SQLite in data/orchestrator/orchestrator.db, owned by orchestrator db.py | Projects, tasks, memories, autonomy runs and handoffs; additive migration currently only adds task mode. |
| Memory service | services/memory-service/.gitkeep | Placeholder; memory is currently embedded in orchestrator SQLite. |
| Shared SDK/types | packages/agent-sdk, packages/shared-types, packages/tool-sdk contain only .gitkeep | No executable shared contract package exists. |
| Additional apps | apps/vscode-extension/.gitkeep, apps/web-ui/.gitkeep | Planned surfaces, not implemented applications. |
| Deployment | deploy/windows-server PowerShell scripts and IIS web.config | Starts Ollama plus the three Python services and enables the supervisor. |

### Trust and safety boundaries

The Local Agent is the only component that should perform host file/process/terminal/Git mutations. The Orchestrator decides what work is allowed, records checkpoints and approvals, and calls Local Agent. The Model Gateway only selects and invokes models. This separation is coherent; the plan must not merge these components.

The current path guard, mutation checkpoint requirement, terminal classification and process controls are valuable foundations. They need to become explicit policy ports consumed by a coordinator rather than remain distributed through a 3,270-line service module.

## 2. Current agent workflow

### Interactive task path

1. POST /v1/agent/tasks creates a persisted agent_tasks row and schedules run_agent_task.
2. run_agent_task resolves project/workspace policy and performs an initial inspection.
3. The model is asked for one structured agent_action at a time (maximum 30 steps, with bounded retries).
4. Read/search actions establish an explicit target. Write/replace/apply-patch actions require a checkpoint and the existing approval policy; execution is delegated to Local Agent.
5. The runner captures diffs, validation commands/results and tool outcomes. Completion requires a meaningful result contract and post-mutation validation where required.
6. Terminal task state, compact evidence and failure information are persisted in SQLite memory.

### Scheduled autonomous path

1. FastAPI lifespan starts the scheduler after startup when AUTONOMOUS_MODE_ENABLED=true.
2. Every five minutes in the server deployment, the scheduler reconciles stale active work, skips if another run is active, and selects one item from a 14-key persisted backlog.
3. The configured role registry is resolved. Read-only roles are batched (parallelism two); each writer is isolated behind a phase barrier. The writer and validation reader are retained even when optional section specialists are disabled.
4. Each specialist is still an ordinary agent_task with a role-specific instruction. Handoffs are persisted with summary, evidence, changed files, validations, blockers and previous handoff IDs.
5. A successful cycle is marked complete only after the writer/validation rules pass. A verified checkpoint may then be pushed by _push_verified_checkpoint.
6. The loop waits for the interval and repeats. There is no product-level completion criterion, acceptance gate, or terminal state for the backlog.

### Current data snapshot

- Projects: 1.
- Agent tasks: 1,110.
- Memories: 1,110 (success 947, failed 163).
- Autonomy runs: 498 (completed 335, failed 163).
- Handoffs: 1,110 (completed 947, failed 157, running 6).
- Observed autonomy range: 15 September 2026 through 17 September 2026 UTC; latest observed run began 17 September 2026 20:57:43 UTC.
- Changed paths recorded in memories: README.md (30 occurrences); no backlog target source file is represented as changed evidence.
- Dominant recorded failure classes: autonomous timeout (74), maximum step limit (30), 900-second timeout (7), restart reconciliation (6), invalid/unsupported model tool calls (multiple occurrences).

## 3. Existing agent roles

The source-of-truth registry in services/orchestrator/app/subagents.py currently defines:

| Key | Title | Current write capability |
|---|---|---|
| monitor | Supervisor Manager | Read-only |
| requirements | Requirements Analyst | Read-only |
| planner | Change Planner | Read-only |
| architect | Architecture Analyst | Read-only |
| inspector | Project Inspector | Read-only |
| orchestrator | Orchestrator Specialist | Read-only |
| gateway | Model Gateway Specialist | Read-only |
| local_agent | Local Agent Specialist | Read-only |
| backend equivalent | No dedicated registry key; closest role is general implementer | Writer capability is not domain-scoped |
| frontend equivalent | No dedicated registry key; closest role is Control Center/Desktop specialist | Read-only |
| ui | Control Center Specialist | Read-only |
| desktop | Desktop Specialist | Read-only |
| implementer | Safe Implementer | Writer; validation required |
| debugger | Bounded Debugger | Writer; validation required; retry |
| tests | Test Specialist | Read-only; validation required |
| verifier | Validation Engineer | Read-only; validation required |
| reviewer | Change Reviewer | Read-only |
| security | Security Reviewer | Read-only |
| integration | Integration and Release Analyst | Read-only |
| docs | Documentation Specialist | Read-only |

Aliases include managermonitor, scoutinspector, local-agentlocal_agent and test-verifiertests. The registry has broad naming coverage, but role names are not yet enforceable organizational contracts: most specialists cannot submit a typed question, challenge, revision request or decision, and domain ownership is not represented in a work DAG.

## 4. Current persistence model

services/orchestrator/app/db.py owns a SQLite database with WAL, a five-second busy timeout, foreign keys and a 30-second connection timeout.

Current tables and indexes:

- projects: project identity and workspace uniqueness.
- agent_tasks: instruction, mode, status, plan, current step, results, approvals, pending action, final output and error; project/status indexes.
- agent_memories: episodic summaries, bounded detail JSON, confidence and usage counters; project/created index.
- autonomy_runs: goal, requested/completed cycles, task IDs, status and error.
- subagent_handoffs: role/section/status, evidence, changed files, validations, blockers, next action, confidence and previous handoff IDs; run/project indexes.

Strengths are durable task/run/handoff history, bounded JSON fields, terminal-memory compaction and foreign-key linkage. Gaps are the absence of durable work-item dependencies, agent identity/session, leases, inbox/outbox messages, acknowledgements, decisions, revision history, validation-run entities, event correlation, cancellation tokens and migration versioning beyond a simple additive column check.

## 5. Current autonomous workflow

The implementation is a bounded improvement loop, not a general project delivery pipeline:

- A fixed 14-key backlog is rotated for fairness; selection uses recent memories and run history.
- Every cycle is limited to one requested cycle, one writer phase and at most two concurrent readers in the server deployment.
- Writers must checkpoint before mutation and a validation reader must succeed before a run can complete.
- The deployment script starts the loop every five minutes and currently sets AUTONOMOUS_AUTO_PUSH=true.
- Checkpoint push verifies repository root, expected remote, branch and a clean tree outside allowed paths before pushing origin HEAD:main.
- There is no intake of an arbitrary external repository, stack/environment detection, isolated project workspace creation, acceptance criteria, multi-stage plan-to-result contract, or final release report.
- Repeated no-op cycles are counted as completed runs; elapsed run count is therefore not a completion metric.

## 6. Current inter-agent communication capabilities

Implemented:

- Role-specific prompts and bounded role markers.
- Persisted SubagentHandoff records with evidence, validations, blockers, confidence and previous_handoff_ids.
- Shared project workspace and SQLite memory search.
- Parallel read-only phases and a serialized writer phase.
- Supervisor-level reconciliation of stale tasks/runs.

Missing:

- A typed message envelope with sender/recipient, thread, reply-to, priority, deadline and idempotency key.
- Durable inbox/outbox delivery with acknowledgement, retry and deduplication.
- Explicit QUESTION, CHALLENGE, REVISION_REQUEST, DECISION and ESCALATION message types.
- Supervisor arbitration records and a decision policy when agents disagree.
- Work-item dependencies and a DAG scheduler that can unblock downstream agents from validated evidence.
- Lease ownership for files/workspaces and conflict detection beyond the single global writer barrier.
- A shared evidence schema that links claims to file hashes, test runs, diffs and checkpoints.
- Pause/resume/cancel semantics that survive process restart.

## 7. Missing capabilities relative to the target system

### P0  execution correctness and safety

1. Stabilize model tool-call parsing and deterministic abort/retry behavior; invalid tool output must never strand a run.
2. Disable automatic remote push by default and require an explicit operator-controlled release action.
3. Add durable cancellation, idempotency, lease expiry and restart-safe state transitions.
4. Define completion as validated acceptance criteria, not a cycle returned without an exception.
5. Prevent stale running handoffs/tasks from accumulating.

### P0  real project intake and delivery

1. Accept an external repository or archive through an explicit intake API.
2. Snapshot and verify the source, create an isolated workspace and retain a rollback point.
3. Detect stack/toolchain from manifests (Python, Node, PHP/Laravel, Docker, etc.) and select bounded build/test commands.
4. Produce a requirements contract, plan/DAG, implementation patches, targeted tests, full tests, debug/retry evidence and final verification report.

### P1  organizational coordination

1. Make role capabilities, ownership and write scopes explicit.
2. Add typed mailbox communication, questions, challenges, revisions and Supervisor decisions.
3. Schedule independent readers in parallel and serialize only conflicting write leases.
4. Route work to role-appropriate model profiles through the Model Gateway public interface.
5. Persist event history so a restarted Supervisor can resume exactly once.

### P1  product and operations

1. Add authenticated operator/project identity and server-side authorization; current APIs have no auth/tenant model.
2. Aggregate validation, cost/latency, approvals, health and checkpoint state for operators.
3. Add restart/watchdog, structured correlation logs, metrics, backup/restore and CI/CD evidence.
4. Bring Desktop dependency installation/build and Provider Router test environment into a reproducible state.
5. Add end-to-end and sample-project smoke coverage without opening/focusing UI during headless service work.

### P2  completeness

- Implement a real memory service only when SQLite boundaries and measured scale require extraction.
- Populate shared type/agent/tool SDKs from the canonical contracts.
- Implement VS Code and web UI surfaces after the core contracts are stable.
- Add deeper domain specialists (backend, frontend, release/verification) as contract-backed adapters rather than prompt aliases.

## 8. Technical debt blocking the target architecture

| Debt | Impact | Proposed treatment |
|---|---|---|
| agent_service.py is 3,270 lines | Tool policy, model protocol, execution and persistence are tightly coupled; changes are risky | Extract pure protocol/guard/execution/runner modules behind compatibility imports; add characterization tests before each extraction. |
| autonomy.py is 944 lines | Scheduler, backlog, phases, reconciliation and Git push policy share one module | Split scheduler, backlog selector, coordinator and release/checkpoint policy. |
| db.py is 689 lines | Connection, schema, repositories, memory compaction and handoffs are mixed | Add migration runner plus repository modules; preserve existing function signatures during transition. |
| Registry is prompt-centric | Role titles do not imply enforceable capabilities, scopes or handoff obligations | Version a role contract with allowed tools, read/write scope, required evidence and escalation rules. |
| Handoff is not a mailbox | Agents cannot ask, challenge, acknowledge or resolve disagreement | Add durable typed messages and Supervisor decision records; retain handoff as a compatibility projection. |
| No DAG/dependencies/leases | Parallelism is coarse and conflicts are discovered late | Add work items, dependency edges, workspace/file leases and idempotency keys. |
| Fixed rotating backlog | Runs can continue forever while making no change | Replace with acceptance-gated work queue and explicit terminal/success state; retain backlog as seed input. |
| Documentation drift | Tauri/Electron, backlog size, test counts and paths disagree with source/runtime | Regenerate docs from source/config and record revision/date. |
| Hard-coded paths | F:\AI-Engineer appears in Electron and examples while server checkout is C:\Services\AI-Engineer\current | Centralize environment-derived roots and validate at startup. |
| Auto-push enabled in deployment | Autonomous code can reach GitHub without an explicit release action | Set false in deployment and examples; require a separate reviewed release command. |
| ChatTaskRequest allows arbitrary extras | Contract/mass-assignment risk and weak API evolution | Set strict input models and explicit extension fields; add negative tests. |
| No authentication/rate limiting | Any reachable API caller can enumerate or mutate project/task state | Add operator identity, authorization, CSRF/CORS policy and rate limits before exposure beyond loopback. |
| Placeholder memory/SDK/apps | Target architecture cannot share canonical contracts or support promised clients | Implement only after coordination contracts are stable; mark placeholders honestly meanwhile. |
| Reproducibility gaps | Desktop has no installed Vite; Provider Router has no Vitest in the current checkout | Pin/install dependencies in CI and deployment validation; distinguish missing tooling from code failures. |

## 9. Tests currently passing/failing

These are fresh commands executed against the audited checkout; no source changes were made to obtain the results.

| Check | Command | Result |
|---|---|---|
| Orchestrator unit suite | services/orchestrator/.venv/Scripts/python.exe -m unittest discover -s tests -q | PASS  62 tests |
| Local Agent unit suite | services/local-agent/.venv/Scripts/python.exe -m unittest discover -s tests -q | PASS  2 tests |
| Model Gateway suite | services/model-gateway/.venv/Scripts/python.exe -m pytest -q | PASS  26 tests; deprecation warnings only |
| Python compilation | python -m compileall -q app in all three Python services | PASS |
| Control Center build | apps/control-center npm run build | PASS  tsc + Vite 7.3.6 |
| Desktop build | apps/desktop npm run build | FAIL  vite is not recognized; apps/desktop/node_modules is absent |
| Provider Router suite | services/provider-router npm test | NOT_RUN/FAIL  command cannot start because vitest is not installed; no test assertions executed |
| Lint / standalone typecheck | Repository-wide | NOT_RUN; no unified command and dependencies are incomplete |
| Dependency/security audit | npm/pip audit | NOT_RUN |
| Model Gateway health | GET http://127.0.0.1:8010/health and /health/ready | PASS |
| Local Agent health | GET http://127.0.0.1:8011/health | PASS |
| Orchestrator health/capabilities | GET http://127.0.0.1:8012/health and /capabilities | PASS; supervisor enabled, five-minute interval, one cycle/run |
| Provider Router local health | GET http://127.0.0.1:8020/ | FAIL  connection refused in this checkout |
| Control Center runtime/E2E | Browser/UI startup | NOT_RUN; headless/no-focus policy and no request to exercise the UI |

The older reports under reports/ mention different historical counts and, in places, claim a passing Desktop build. Those claims are not accepted as current evidence; the commands above are the audit baseline.

## 10. Exact files/modules proposed to modify

No source changes are made in this audit. The following is the proposed change set, in dependency order.

### Foundation and contracts

- services/orchestrator/app/schemas.py  strict request models; typed work item, message, evidence, decision and validation schemas.
- services/orchestrator/app/coordination/contracts.py (new)  versioned role/message/work-item contracts.
- packages/shared-types/ (new executable contract package)  generated/shared JSON schema or TypeScript/Python representations.
- project-state.json and project-integrity-manifest.md (new)  stage and preservation evidence.
- docs/01-project-brief.md, docs/01-requirements.md, docs/02-design-system.md and subsequent stage docs  reconcile documentation with source.

### Orchestrator decomposition

- services/orchestrator/app/agent_service.py  compatibility façade only after extracting:
  - app/agent/protocol.py (model action parsing/normalization),
  - app/agent/guards.py (path, checkpoint, approval and validation policy),
  - app/agent/executor.py (Local Agent calls and tool execution),
  - app/agent/runner.py (task state machine and retry/cancel semantics),
  - app/agent/observability.py (events and redacted structured logs).
- services/orchestrator/app/autonomy.py  retain public entry points while delegating to:
  - app/coordination/scheduler.py,
  - app/coordination/backlog.py,
  - app/coordination/reconciliation.py,
  - app/release/checkpoint_policy.py.
- services/orchestrator/app/db.py  compatibility façade over repositories/migrations.
- services/orchestrator/app/coordination/{dag,mailbox,leases,decisions,event_log}.py (new).
- services/orchestrator/app/subagents.py  role contracts, capabilities and domain scopes.
- services/orchestrator/app/routers/agent.py, routers/tasks.py and main.py  versioned coordination/intake/status endpoints and middleware hooks.

### Project intake and execution

- services/orchestrator/app/intake.py (new)  archive/repository intake, manifest validation and provenance.
- services/orchestrator/app/workspaces.py (new)  isolated workspace, snapshot, backup and rollback lifecycle.
- services/orchestrator/app/environment_detection.py (new)  stack detection and bounded command profiles.
- services/local-agent/app/services/files.py, git_tools.py, terminal.py, processes.py  expose policy ports needed by workspace leases/intake without widening host authority.
- services/local-agent/app/config.py and services/orchestrator/app/config.py  remove hard-coded roots; production-safe defaults.
- services/model-gateway/app/router.py, provider interfaces and config  role/model profile routing through the existing public gateway interface only.

### Operator, security and operations

- services/orchestrator/app/auth/ (new), authorization middleware and rate-limit adapter.
- services/orchestrator/app/routers/health.py and main.py  readiness, event correlation and safe operational metrics.
- apps/control-center/src/api.ts, App.tsx  typed work DAG, mailbox, validation, approval and health views after API contracts stabilize.
- apps/desktop/electron/main.cjs, src/App.tsx  environment-derived service roots and operator controls; retain Electron boundary.
- deploy/windows-server/start-ai-engineer-server.ps1, register-ai-engineer-task.ps1, health-check.ps1, README.md  auto-push false, explicit release action, dependency preflight, watchdog/restore checks.
- .env.example files  safe placeholders and consistent defaults; never real credentials.
- services/provider-router  no direct edits planned; only public-interface integration and reproducible dependency setup.

### Verification

- services/orchestrator/tests/test_agent_service.py (new characterization/regression coverage), existing test_autonomous_backlog.py, test_subagents.py, test_config.py.
- New tests for coordination contracts, leases, DAG scheduling, mailbox delivery, restart/resume, idempotency, acceptance gates and security boundaries.
- services/local-agent/tests and services/model-gateway/tests for changed contracts.
- apps/control-center component/API tests and a small Playwright smoke suite when a display-independent runner is available.
- CI workflow and dependency lockfiles for each independently buildable package.

## 11. Proposed final architecture

### Orchestrator as a modular coordinator

                    Orchestrator
  Intake -> Requirements -> Plan/DAG -> Coordinator
                                  |          |
                       typed mailbox/event log
                                  v          v
                 Role adapters (stateless, bounded)
       inspector / planner / architect / backend / frontend
       implementer / tester / debugger / reviewers / release
                                  |
                           Validation gates
                                  |
                        Supervisor decision record
                                  |
                  checkpoint + report + explicit release

- Intake module owns provenance, project registration, stack detection and isolated workspace creation.
- Planning module turns requirements into versioned work items and dependency edges.
- Coordination module persists a DAG, leases and typed messages; schedules independent readers in parallel and grants one writer lease per conflicting scope.
- Role adapters receive a typed work item and evidence context. They never mutate the host directly.
- Execution/policy module remains the only Orchestrator path to Local Agent tools; every mutation has checkpoint, approval and validation requirements.
- Validation module runs targeted then full checks, records command/output digests, and closes acceptance criteria.
- Memory module stores validated experiences and failure causes. Keep it in SQLite until measured scale warrants extraction.
- Supervisor owns arbitration, re-planning, retry budgets, safe stop/resume and the final release decision.
- Model Gateway remains an independent model/provider boundary and can route role profiles; Provider Router remains behind its public contract.
- UI/Desktop consume versioned APIs and event projections; they do not gain direct filesystem or model access.

### Persistence additions

Add migration-safe tables (names are illustrative and must be reconciled with existing conventions):

- work_items, work_item_dependencies, work_item_attempts;
- agent_identities, agent_sessions, agent_leases;
- messages (inbox/outbox, type, thread, reply-to, idempotency);
- decisions, revision_requests, validation_runs, acceptance_criteria;
- checkpoints, event_log, run_locks.

Retain existing task/run/memory/handoff tables and provide compatibility projections until downstream clients migrate.

### Completion and safety invariants

- A work item can close only when its acceptance criteria have evidence-backed validation.
- Every mutation is scoped to a lease, checkpointed, diffed and validated.
- A duplicate message, retry or restart is idempotent.
- A stale lease is reclaimed only after expiry and event logging.
- A disagreement produces a Supervisor decision or an explicit blocked state.
- Remote Git push is never automatic in development; release requires an explicit, auditable operator action.

## 12. Phased implementation plan

### Phase 0  Audit and preservation baseline

Scope: this audit, integrity manifest, project state and corrected documentation.

Gate: source inventory and test baseline are reproducible; no protected route/feature disappears.

### Phase 1  Execution contract stabilization

Files: agent protocol/guards/executor/runner extraction, schemas, tests, config and deployment auto-push setting.

Deliverables: deterministic invalid-tool handling, strict request schemas, cancellation/idempotency, redacted events, stale-run reconciliation.

Gate: existing 62/2/26 Python suites remain green; mutation/approval/checkpoint regression tests pass; no push occurs.

### Phase 2  Durable coordination primitives

Files: new coordination contracts/mailbox/DAG/lease/decision/event modules, SQLite migrations/repositories, subagent role contracts.

Deliverables: typed work items and messages, question/challenge/revision/decision semantics, dependency-aware scheduling, per-scope writer leases with the existing global barrier as fallback.

Gate: restart/resume, duplicate-delivery, conflict and arbitration tests pass; old handoff API remains compatible.

### Phase 3  Real project intake and workspace lifecycle

Files: intake/workspace/environment modules, orchestrator routes, Local Agent policy ports and configuration.

Deliverables: secure repository/archive intake, provenance, isolated workspace snapshot, manifest-based stack detection and bounded command profile.

Gate: sample projects for Python, Node and PHP can be registered, snapshotted, tested and rolled back without escaping the workspace.

### Phase 4  Role-specialist execution

Files: subagent registry/contracts, coordinator, model-gateway role profiles, role-specific tests.

Deliverables: enforceable Supervisor, Requirements, Planner, Architect, Researcher, Backend, Frontend, Implementer, Test, Debug, Code Review, Security, Integration, Documentation and Release roles.

Gate: a work DAG executes independent readers in parallel, serializes conflicting writers, routes evidence to the next role and records Supervisor decisions.

### Phase 5  Complete plan-to-tested-result loop

Files: autonomy scheduler/coordinator, validation/retry modules, persistence, API projections and tests.

Deliverables: requirements  plan  patch  targeted tests  full tests  debugger/retry  review/security  final verification/report; pause/resume/cancel and bounded retry.

Gate: sample-project E2E run reaches a validated final result or a truthful blocked state; no no-op run is counted as successful delivery.

### Phase 6  Operator observability and clients

Files: health/status routers, control-center API/App, Electron preload/main/App.

Deliverables: live DAG/mailbox/validation/approval/decision/health views, retry and safe-stop controls, error/empty/offline states, environment-derived service URLs.

Gate: API contract tests and headless UI smoke tests pass; Desktop dependencies build from a clean install.

### Phase 7  Security and production operations

Files: auth/authorization modules, middleware, CORS/rate limits, secrets/config, deployment scripts, CI/CD, backup/restore docs.

Deliverables: authenticated operator/project scopes, audit events, secure secret handling, readiness/watchdog, CI gates, migration/restore runbook, explicit release action with auto-push disabled.

Gate: negative authorization/security tests pass; clean production-like build, health and restore smoke checks pass; no Critical/High finding remains.

### Phase 8  Independent release gate

Files: twelve-stage artifacts, project-state.json, integrity manifest, final reports and release manifest.

Deliverables: requirement traceability, complete validation matrix, known limitations, sanitized release package and rollback instructions.

Gate: no P0/P1 or Critical/High issue, all runnable required checks pass, unavailable checks are marked NOT_RUN, and protected-project integrity is preserved.

### Cross-phase rules

- Keep all changes incremental and behind compatibility façades.
- Do not modify Provider Router internals unless a proven public-interface gap requires it.
- Do not open/focus UI during headless service validation.
- Back up the affected files before every edit or deletion and verify the backup.
- Run targeted checks for changed files; run the full project suite at each phase gate.
- Do not push to any remote repository during implementation.

## CURRENT STATE

A locally runnable multi-service core exists: FastAPI Orchestrator, Local Agent, Model Gateway, Electron Desktop, React Control Center, SQLite memory, guarded tools, checkpoints and a bounded supervisor. The supervisor is enabled on the server and has produced hundreds of persisted runs, but evidence shows mostly no-op/recovery work rather than completed product changes.

## PROBLEMS

The principal blockers are invalid model tool-call output and timeout/step exhaustion, no completion/acceptance gate, no external-project intake, no DAG or durable inter-agent messaging, no Supervisor arbitration, incomplete restart/idempotency semantics, absent auth, stale/hard-coded configuration, documentation drift, missing Desktop/Provider Router dependencies, and auto-push enabled in deployment.

## TARGET ARCHITECTURE

Preserve UI/Desktop  Orchestrator  Local Agent/Model Gateway. Evolve the Orchestrator into a modular coordinator with typed role contracts, a durable work DAG, mailbox/event log, leases, Supervisor decisions, acceptance-gated validation and restart-safe state. Keep Local Agent as the host trust boundary and Model Gateway as the provider boundary. Keep SQLite initially, adding migration-safe coordination tables; add a separate memory service only when scale justifies it.

## IMPLEMENTATION PHASES

1. Stabilize execution/tool contracts and disable auto-push.
2. Add typed coordination, mailbox, DAG, leases and decisions.
3. Build secure project intake, snapshots and stack detection.
4. Enforce domain-specialist role contracts and model profiles.
5. Complete plan-to-tested-result, retry, review and resume loop.
6. Add operator observability and clean-build client integration.
7. Add authentication, security hardening, CI/CD, watchdog and backup/restore.
8. Run independent release/integrity gate and package the verified artifact.

## FILES TO CHANGE

Primary changes are confined to Orchestrator contracts/coordinator/persistence/routers/tests, Local Agent policy/config, Model Gateway public routing/config, Control Center and Electron API clients, deployment/configuration/docs, and new coordination/intake/auth modules listed in Section 10. Provider Router internals and unrelated UI redesign are explicitly out of scope.

## TEST BASELINE

PASS: Orchestrator 62 unittest tests; Local Agent 2 unittest tests; Model Gateway 26 pytest tests; Python compileall for all three services; Control Center npm run build; live health for ports 8010/8011/8012 and Orchestrator capabilities.

FAIL/NOT_RUN: Desktop build cannot start because Vite/node_modules are absent; Provider Router test command cannot start because Vitest is absent; Provider Router local port 8020 is not listening; repository-wide lint, standalone typecheck, dependency audit and browser E2E are not run.

## RISKS

The largest risks are scope expansion while refactoring the large orchestrator modules, introducing coordination races, weakening host-path or approval controls, allowing duplicate/replayed mutations, and accidentally re-enabling remote push. Mitigate with compatibility façades, migration tests, lease/idempotency tests, adversarial security tests, verified backups before edits, explicit release authorization and phase gates.

## Audit conclusion

The current system is a sound local execution foundation but not yet the requested autonomous multi-agent engineering organization or a production-ready accept any project and return a tested result service. The plan above is intentionally incremental: it preserves working boundaries and safety controls while adding the missing organizational, evidence, reliability and release primitives.
