# Autonomous sub-agent pipeline

The orchestrator runs one bounded specialist pipeline per autonomous cycle. The
pipeline is sequential so the implementer can use the scout and planner
observations, while the verifier and reviewer see the resulting task memory.

| Role | Default permission | Responsibility |
| --- | --- | --- |
| `scout` | Read-only | Inspect the current project and collect evidence. |
| `planner` | Read-only | Select one small, high-value improvement. |
| `implementer` | Read + one mutation | Make one checkpointed change and validate it. |
| `verifier` | Read + validation | Run the real project validation command. |
| `reviewer` | Read-only | Review the final scope and evidence. |

The registry lives in `services/orchestrator/app/subagents.py`. The supervisor
creates one ordinary autonomous Agent task for each configured role, so the
existing path guards, Git checkpoint, diff, validation, retry, and memory logic
remain shared. A role is not an unrestricted background process: it is a
bounded task with a clear permission contract.

Configure the pipeline with:

```text
AUTONOMOUS_SUBAGENTS=scout,planner,implementer,verifier,reviewer
AUTONOMOUS_MAX_SUBAGENTS=5
```

The live model/provider routing is exposed at
`GET /v1/runtime/models`; the active local setup is documented in
`docs/active-models.md`.
