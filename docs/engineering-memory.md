# Engineering Memory and Experience-Based Learning

## Scope

This Phase 3 implementation adds evidence-gated engineering experience to the existing Orchestrator. It does not retrain or modify the underlying language models. Learning is implemented as retention, retrieval, feedback, failure-pattern reuse, and measurable routing context.

## Memory Model

The persistence layer supports five memory types:

- `working`: short-lived run/task context.
- `episodic`: facts about what happened in a run.
- `project`: durable project conventions, architecture facts, and commands.
- `lesson`: validated successful engineering patterns.
- `failure`: sanitized failure observations and fixes.

Memory rows carry project/run/task scope, role/task type, structured content, evidence, confidence, usefulness, usage counters, and lifecycle. Candidate observations are excluded from normal retrieval; run/task-scoped candidates are visible only to their originating context.

## Validation Model

Lifecycle states are `candidate`, `validated`, `trusted`, `superseded`, and `rejected`. Promotion requires non-empty evidence. A candidate cannot jump directly to `trusted`. Successful outcomes with tests or accepted review promote a candidate to `validated`; repeated successful uses promote validated memory to `trusted`. Superseded and rejected memories are excluded from retrieval.

Evidence is sanitized and can include test commands/results, review decisions, artifact references, changed files, and supervisor observations. Raw conversational text is not promoted automatically.

## Retrieval Process

`MemoryStore.retrieve` scopes by project (including global memories), role, task type, run/task, query terms, and relevant files. Results are ranked by confidence, usefulness, project/role/task relevance, query/file matches, lifecycle, and recency. Results are bounded to prevent unrelated history from entering an agent context. `ContextBuilder` adds only the bounded records relevant to the current task and preserves the existing validated-memory contract.

## Learning Loop

Supervisor result, failure, and revision paths extract a sanitized lesson or failure memory. The autonomous loop records specialist outcomes and injects retrieved experience into the next cycle. Each use can record success, test result, review acceptance, rework, and evidence. Outcomes update confidence/usefulness counters without fabricating intelligence scores.

Failure observations are normalized into recurring signatures. Repeated signatures increment occurrence/confidence and retain the latest linked memory and successful fix for reuse.

## Agent Metrics

`agent_performance` stores measurable counters per role/model profile/domain: attempts, completions, review rejections, test failures, retries, total duration, and successful domains. The Supervisor status endpoint exposes these statistics for future routing decisions. No subjective or synthetic capability score is persisted.

## Database Changes

Schema version is now `4` with idempotent migration support for:

- `experience_memories`
- `experience_outcomes`
- `failure_patterns`
- `agent_performance`

Foreign keys and indexes follow the existing SQLite initialization path. Existing tables and data are preserved; isolated tests can use temporary database paths.

## API Surface

The coordination router exposes:

- `GET/POST /v1/coordination/memories`
- `POST /v1/coordination/memories/{memory_id}/promote`
- `POST /v1/coordination/memories/{memory_id}/outcome`
- `GET /v1/coordination/performance`
- `GET /v1/coordination/failure-patterns`

Existing coordination, Supervisor, ContextBuilder, and autonomous-run APIs remain compatible.

## Memory Safety

Sanitization redacts private keys, bearer/basic tokens, common API-token formats, password/secret assignments, and credential-bearing database URLs. Secret-like input is never retained verbatim. Stored evidence and notes are bounded and JSON-encoded.

## Test Results

| Component | Command | Result |
|---|---|---|
| Orchestrator | `.venv\\Scripts\\python.exe -m unittest discover -s tests -p 'test*.py' -v` | **PASS - 78 tests** |
| Memory subsystem | `python -m unittest tests/test_memory.py -v` | **PASS - 6 tests** (included in orchestrator suite) |
| Model Gateway | `.venv\\Scripts\\python.exe -m pytest -q` | **PASS - 26 tests** |
| Local Agent | `.venv\\Scripts\\python.exe -m unittest discover -s tests -p 'test*.py' -v` | **PASS - 2 tests** |
| Local Agent pytest command | `pytest -q` | **NOT_RUN - pytest is not installed in that environment** |
| Python compile check | `python -m compileall app` | **PASS** |
| Migration smoke test | isolated temporary SQLite database | **PASS - schema version 4** |
| Service health | `/health` on ports 8010, 8011, 8012 | **PASS** |

## Limitations

- Memory ranking is deterministic lexical/scored retrieval; no embedding index is introduced.
- Promotion evidence is validated structurally, not cryptographically.
- Metrics are descriptive and are not, by themselves, an automatic model-selection policy.
- Extraction occurs at Supervisor/autonomous-loop boundaries; arbitrary chat is not ingested.
- Local Agent's optional pytest command remains unavailable until its environment installs pytest.

## Phase Boundary

Phase 3 is complete at the memory subsystem boundary. Further work should add richer planner/routing policies and integration coverage only after this checkpoint is reviewed; no Phase 4 work is started by this change.
