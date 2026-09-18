# Durable Autonomous Execution and Recovery

- Project: AI-Engineer
- Phase: 5
- Gregorian date: 2026-09-18
- Jalali date: 1405-06-27
- Status: Implemented in the orchestrator core; external deployment remains unchanged.

## Recovery state machine

Runs and tasks retain durable state in SQLite. A startup/scheduler recovery pass classifies every referenced task as:

- `safe_to_resume`: queued/planning work or stale work without evidence of a partial mutation.
- `needs_verification`: expired active work with results/checkpoints or an active recovery state.
- `waiting_for_dependency`: provider, Local Agent, worker, or dependency outage with a retry time.
- `waiting_for_approval`: explicit approval is still required.
- `orphaned`: a referenced task cannot be found or has an invalid state.
- terminal: completed, failed, or cancelled.

Only safe or explicitly verified work is requeued. Running work is never silently marked successful.

## Startup behavior

`initialize_database` applies schema migration 6, then the FastAPI startup hook invokes `recover_incomplete_runs`. The same reconciliation runs from the autonomous scheduler. Expired leases are marked expired, stale tasks are classified, recovery events are written with idempotency keys, and the run is moved to `queued`, `waiting_dependency`, or `recovery_required`. The `/v1/recovery/status` endpoint exposes the persisted classification.

The resume endpoint requires `verify=true` for a run or task requiring verification. Repeating a resume request after normalization is a no-op.

## Lease design

Task execution uses an SQLite-backed `execution_leases` table with a unique resource and lease token. The worker owner, token, heartbeat, expiry, and state are persisted on both the lease and task rows. The agent service acquires a lease before execution, renews it periodically, and releases it in a finally block. A live lease produces a conflict; an expired lease can be taken over. A task lease does not grant permission to write outside the existing workspace policy.

## Failure handling

Provider/model, Local Agent, and worker timeouts are mapped to explicit waiting states. The task retains a sanitized error, dependency kind, provider/fallback metadata, retry time, and attempt count. Provider failures are persisted in `provider_failures`; recovery events provide an audit trail. The existing Model Gateway fallback remains the provider-selection boundary, while recovery preserves the run when all providers are temporarily unavailable.

## Durable persistence

Migration 6 adds recovery columns to `agent_tasks` and `autonomy_runs`, plus `execution_leases`, `recovery_events`, and `provider_failures`. Existing rows and earlier schema versions are preserved through additive, idempotent migration logic. Task IDs are attached to their run when autonomous tasks are created so queued work can be resumed after a process restart.

## API surface

- `GET /v1/recovery/status`
- `POST /v1/recovery/runs/{run_id}/resume`
- `POST /v1/recovery/tasks/{task_id}/lease`
- `POST /v1/recovery/tasks/{task_id}/heartbeat`
- `POST /v1/recovery/tasks/{task_id}/release`

These routes expose recovery operations for future Control Center use without changing existing task/run APIs.

## Validation

The deterministic recovery suite covers lease idempotency and conflicts, stale takeover, dependency pause and redaction, startup classification, verification-gated resume, duplicate resume calls, completed-task preservation, and provider-failure evidence. The full orchestrator, gateway, and Local Agent suites are run as part of the Phase 5 validation pass.

## Known limitations

- Recovery can persist and classify work, but a task requiring verification still needs an explicit verification decision before execution.
- The scheduler resumes queued task IDs sequentially; independent queued tasks are not yet scheduled with a separate bounded parallel queue.
- SQLite remains the single-process persistence authority for this deployment shape. Multi-host orchestration would require a shared transactional database and distributed lease policy.
- No remote Git push is performed by autonomous recovery.
