# Autonomous improvement queue

The five-minute supervisor now selects one concrete source target per run. Each
target is passed to every specialist, and the implementer is required to read
that target before proposing a patch. A run is considered complete only after
the normal checkpoint, non-empty diff, and validation guards succeed.

Current bounded queue:

1. `services/orchestrator/app/autonomy.py` — restart-safe resume and stale-run reconciliation.
2. `services/orchestrator/app/routers/agent.py` — task/run observability.
3. `services/orchestrator/app/db.py` — bounded memory persistence and compaction.
4. `services/orchestrator/app/subagents.py` — specialist contracts and status evidence.

The queue rotates across process restarts and prefers targets that have not been
changed in recent task memory. It never installs dependencies, publishes code,
or edits outside the selected project-relative target.
