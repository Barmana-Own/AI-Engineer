# End-to-End Multi-Agent Engineering Validation

## Scope

This fixture validates the existing orchestrator coordination engine without changing the desktop or React UI. It accepts the objective:

> Create a small service with an API endpoint, validation, tests, documentation and a simple frontend client.

The fixture runs real SQLite persistence, task transitions, dependency scheduling, workspace locks, message publication, handoffs, memory promotion, subprocess test execution, reviewer revision handling, and restart recovery. Model calls are intentionally deterministic in CI; an opt-in real-model smoke test is provided separately.

## Workflow Evidence

1. Supervisor receives and persists the objective.
2. Requirements, planner, and architect tasks produce persisted results and handoffs.
3. Backend, frontend, and shared implementer tasks execute concurrently in independent scopes.
4. Integration and documentation tasks produce a runnable fixture workspace.
5. The tester executes `unittest` as a real subprocess. The first run fails against an intentionally incorrect implementation.
6. The Supervisor records the failure; debugger repairs the implementation and the tester reruns successfully.
7. Reviewer rejects the first submission, requests a revision artifact, and accepts the resubmission.
8. Release verification checks required files and executes the tests again.
9. A simulated orchestrator restart reloads durable state and the final Supervisor result references persisted evidence.

## Trace Format

Each run writes an atomic JSON projection next to its database as `<database-stem>.trace.<run-id>.json`. The trace includes ordered events, task state snapshots, role assignments, persisted messages, handoffs, workspace file hashes, test executions, review/revision events, lessons, and the final evidence result. `GET /v1/coordination/runs/{run_id}/trace` exposes the projection for an existing run.

The SQLite database remains the source of truth for tasks, messages, handoffs, locks, runs, and memories. The JSON projection is restart-safe observability and can be rebuilt from persisted state.

## Validation Commands

From `services/orchestrator`:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_e2e_workflow -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test*.py' -q
.\.venv\Scripts\python.exe -m py_compile app/coordination/e2e.py app/coordination/supervisor.py app/routers/coordination.py
```

The optional real-model smoke test runs only when `AI_ENGINE_REAL_MODEL_SMOKE=1` and the model gateway is explicitly configured. It is skipped otherwise and is not treated as deterministic CI evidence.

## Acceptance Coverage

| Requirement | Evidence |
| --- | --- |
| Persisted agent messages | `message_published` events and `agent_messages` rows |
| Persisted handoffs | `handoff` events and `subagent_handoffs` rows |
| Dependency gating | scheduler transitions and completed task graph |
| Parallel independent work | `parallel_batch_started`/`completed` events |
| Writer conflict protection | lock probe records first acquisition and second denial |
| Real test execution | failed and passing `test_execution` events from subprocesses |
| Repair cycle | tester blocker, debugger handoff, tester retry |
| Review revision cycle | `review_rejected`, `REVISION_REQUEST`, revision artifact, acceptance |
| Validated memory | promoted lesson linked to tests and review evidence |
| Restart recovery | `orchestrator_restart` and `startup_recovery` events |
| Final evidence | Supervisor `final_result` with completion and evidence list |

## Limitations

The fixture is a deterministic integration validation, not a claim that a language model was retrained. The real-model smoke path is opt-in and was not run when model credentials/configuration are absent. UI automation and remote deployment are outside this validation scope.
