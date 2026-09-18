# Current Roadmap (Verified 2026-09-18 / 1405-06-27)

> Status: maintained roadmap. Historical Tauri/Rust plans are obsolete because `apps/desktop` is Electron.

## Verified baseline

- FastAPI Orchestrator, Model Gateway and Local Agent run as separate services.
- SQLite schema/migration version 6 is deterministic and additive.
- Canonical role registry, dependency-aware coordination DAG, persisted message bus, handoffs, memory lifecycle, self-improvement gates and restart recovery are implemented.
- Control Center production build passes in the audited environment.
- Deterministic end-to-end coordination fixture exercises persistence, dependency scheduling, locks, messages, handoffs, subprocess tests, review/revision and restart trace.

## Next development priorities

### P0  release confidence

1. Install and pin the missing Desktop and Provider Router Node dependencies, then run their build/test suites in CI.
2. Add a real specialist-worker adapter contract so the Supervisor can dispatch role contracts through the Model Gateway while retaining the existing agent loop.
3. Harden scheduler conflict detection so reader/writer overlap is rejected regardless of task iteration order.
4. Add integration tests for multi-process deployment expectations or explicitly enforce single-process operation.

### P1  operability

1. Add metrics and structured trace correlation for task leases, provider fallback and recovery classifications.
2. Exercise migration upgrades from representative pre-version-6 databases in CI.
3. Add a subject-scoped discussion counter and enforce confidence/timeout policy in the discussion controller.

### P2  product expansion

1. Replace placeholder SDK/memory-service packages only when a concrete consumer and compatibility contract exist.
2. Add optional vector/semantic retrieval behind the current deterministic lexical retrieval interface.
3. Expand role-specific acceptance contracts and domain-specific task templates.

## Guardrails

Autonomous execution, autonomous improvement and remote Git push remain disabled unless explicitly configured. Any future worker parallelism must preserve transactional workspace locks, bounded retries, evidence gates and restart-safe state.
