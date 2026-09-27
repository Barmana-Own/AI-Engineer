# Software-Delivery Skills

This directory contains the twelve imported software-engineering playbooks used as preserved reference material for AI-Engineer.

The authoritative registry is [`manifest.json`](manifest.json). The Orchestrator database remains authoritative for projects, tasks, runs, and execution state. Any `project-state.json` consumed by an imported playbook is a compatibility view only.

Skill activation is `router_only`: the existing AI-Engineer router must select a skill for a scoped task, role, and project. The `allow_implicit_invocation` value in an imported `agents/openai.yaml` is retained for auditability and is never an activation grant.

Bundled scripts are classified in [`import-report.md`](import-report.md). They are not model tools. Any future execution must pass through the Agent Worker, tool policy, Local Agent, workspace boundary, command/network policy, timeout/output limits, and approval policy.

Phase 10A only imports and validates the materials. It does not connect skills to live agents or impose a global Stage 01–12 pipeline.

The compatibility adapter is implemented by `services/orchestrator/app/skill_state.py`. It reads projects, tasks, and autonomy runs from SQLite and can render an explicit read-only Stage State artifact; it does not accept workflow mutations from skills.

## Phase 10B routing integration

`role-skill-map.json` is the single role-to-skill policy consumed by `services/orchestrator/app/skill_routing.py`. It is conditional and task-scoped; it does not enforce the imported Stage 01–12 sequence globally. Selected skills, stage dependencies, and structured evidence are recorded on the existing `agent_tasks` trace. Context is loaded lazily through the registry and permissions remain the intersection of role, task, skill, and global policy.
## Phase 10C execution gateway

The imported helpers remain preserved playbook material and are not unrestricted model tools. `services/orchestrator/app/skill_script_gateway.py` resolves only manifest-declared scripts and requires the existing Agent Worker → Tool Policy → Local Agent chain. It delegates command execution to the Local Agent after exact repository-command, role/task/global capability, workspace, timeout, output, network-target, redirect, and approval checks. It never invokes `subprocess`, performs HTTP requests, or writes artifacts directly. Evidence writes are limited to `docs/`, `artifacts/`, and `reports/`; `project-state.json` is handled only by the database compatibility adapter. Secret-bearing output and headers are redacted before persistence.

High-risk or Local Agent approval-required actions require a server-side approval verifier bound to the canonical action hash. The legacy boolean approval field is only a downstream compatibility signal and cannot authorize a script. Live worker binding remains an explicit runtime integration step; no helper can bypass this gateway.
### Explicit command-plan gate

`COMMAND_RUNNER` and `TEST_RUNNER` helpers also require an explicitly authorized task plan (`task_plan_authorized`). A model cannot authorize a command by supplying its own `declared_commands`; the worker must derive and authorize the plan from trusted repository/skill metadata before Local Agent execution.
## Phase 10D validation

The deterministic skill-aware execution scenarios are implemented in `services/orchestrator/tests/test_skill_execution_scenarios.py`. They use the existing router, lazy context loader, permission intersection, quality gates, and SQLite task trace. Scenario A covers a full-stack authentication project; B a backend migration defect; C frontend accessibility; D an authentication/security repair; and E release validation. The machine-readable evidence is stored in `reports/phase10d-skill-execution-trace.json`.

The scenarios demonstrate contextual selection and exclusion of irrelevant skills. They are not a live-model execution claim: the selected context is ready for the existing Agent Worker, but a production worker must still invoke the Model Gateway with this contract and persist its real execution result.