> **Implementation status (2026-09-18 / 1405-06-27):** The autonomous supervisor is interval-configured and bounded; the default interval is five minutes, but autonomous mode is disabled unless explicitly enabled. Remote Git auto-push remains disabled.\n\n# Autonomous improvement queue

The interval-configured bounded supervisor (default the configured interval (five minutes by default)) now selects one concrete source target per run. Each
target is passed to every specialist, and the implementer is required to read
that target before proposing a patch. A run is considered complete only after
the normal checkpoint, non-empty diff, and validation guards succeed.

Current bounded queue:

1. `services/orchestrator/app/autonomy.py` â€” restart-safe resume and stale-run reconciliation.
2. `services/orchestrator/app/routers/agent.py` â€” task/run observability.
3. `services/orchestrator/app/db.py` â€” bounded memory persistence and compaction.
4. `services/orchestrator/app/subagents.py` â€” specialist contracts and status evidence.

The queue rotates across process restarts and prefers targets that have not been
changed in recent task memory. It never installs dependencies, publishes code,
or edits outside the selected project-relative target.

