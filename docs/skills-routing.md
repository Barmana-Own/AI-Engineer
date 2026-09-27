# Skill Routing and Dynamic Workflow

## Scope

Phase 10B connects the twelve imported software-delivery playbooks to existing AI-Engineer roles. A skill remains a playbook and is never an agent, task queue, or workflow state store. The orchestrator database remains authoritative for tasks and execution state.

## Registry and policy

`skills/software-delivery/manifest.json` is the installed skill registry. `skills/software-delivery/role-skill-map.json` is the single canonical role-policy extension consumed by `app.skill_routing.SkillRouter`. The router validates every referenced skill through `SkillRegistry`; unknown IDs fail closed.

The external `agents/openai.yaml` metadata is retained for audit, but `allow_implicit_invocation` cannot activate a skill. Activation requires an explicit router selection plus task, role, and project scope.

## Role-to-skill selection

The policy contains required and optional rules. Conditions are evaluated against the bounded task objective, project type, requirements, risk, technologies, and phase. Current examples include:

| Role | Required baseline | Conditional support |
| --- | --- | --- |
| Requirements / Project Manager | Project analysis | None |
| UX Designer | Design-system UI architecture | None |
| Frontend | Design-system UI architecture, frontend architecture | API integration when an interface is involved |
| Architect | Project analysis | Backend, API, frontend, and database architecture when indicated |
| Backend | Backend architecture | Database, API, and authentication/authorization when indicated |
| Integration | API integration | None |
| Security | Application security | Authentication/authorization when identity or access control is in scope |
| Tester | Software testing, QA/debugging | None |
| Debugger | QA/debugging, software testing | None |
| DevOps | Deployment-production | None |
| Reviewer | Software testing, full-stack final review | Application security for security-sensitive changes |
| Release Verifier | Full-stack final review | Deployment-production when release operations are in scope |

SEO, Sales, and documentation roles remain compatible with the registry but do not receive unrelated engineering playbooks by default.

## Task and project routing

`SkillRouter.route(SkillRouteRequest(...))` returns `SkillSelection` records containing `skill_id`, reason, priority, required/optional mode, and the condition that matched. `route_project` derives a project-level set only when the objective justifies it.

Examples:

- A backend SQLite migration selects backend architecture and database architecture; it does not select UI skills.
- A responsive React layout selects design-system and frontend architecture; it does not select database architecture.
- An authentication review selects authentication/authorization and application security.
- A documentation-only request selects no engineering stages.
- A full-stack application selects the relevant UI, frontend, backend, API, testing, security, and final-review skills. Deployment is added only when deployment is part of the objective.

The router adapts stage dependencies to the selected set. It does not impose a universal Stage 01–12 pipeline. Dependencies are represented as a derived `StageDependency` trace and are not a second task graph.

## Lazy context loading

`SkillContextLoader` accepts only an explicit `SkillRouteResult` for the executing role and loads the selected skill's `SKILL.md` only after the router has approved a scoped task. References are loaded only when the worker names a reference declared by that skill. Document and reference byte limits prevent uncontrolled context amplification. Skill scripts are not executed by this module and remain behind the Agent Worker → Tool Policy → Local Agent boundary.

## Evidence and quality gates

Workers can persist the structured `SkillExecutionEvidence` contract:

- `skill_id`
- `task_id`
- `agent_id`
- `artifacts_created`
- `checks_run`
- `findings`
- `gate_status`
- `handoff`
- `evidence`

Required gates use objective evidence. Testing requires a passing test signal and recorded checks; QA requires regression evidence; security requires resolved findings and checks; deployment requires health checks; final review requires acceptance, no critical findings, and checks. A free-form self-reported PASS is not sufficient.

## Permission model

Effective tools are the intersection of:

`role permissions ∩ task permissions ∩ selected skill requirements ∩ global policy`

A skill can narrow a role's capabilities but cannot grant a role a tool it does not already have. Filesystem, terminal, Git, approval, and network safety remain enforced by the existing Local Agent and policy layers.

## Persistence and API compatibility

The existing `agent_tasks` table now has idempotent `skill_selections_json` and `skill_trace_json` columns. Existing databases receive the columns during normal initialization without data loss. `db.set_task_skill_route` writes the router output to the existing task record, and `db.append_task_skill_evidence` appends structured execution evidence to that same trace. Task API responses expose `skill_selections` and `skill_trace`; task creation accepts optional scoped routing inputs while all prior fields remain compatible.

No skill module writes `project-state.json` or creates a competing workflow store. Any stage-state view remains a read-only compatibility projection of the database.

## Validation

The deterministic routing suite covers role selection, contextual project stages, lazy references, permission intersection, objective quality gates, structured evidence, unknown-role rejection, and task persistence. The complete orchestrator test suite is the release evidence for this phase.

Phase 10B does not connect skills to live worker execution or enforce a global twelve-stage pipeline; those are separate runtime concerns.
## Phase 10C script execution hardening

Imported helper scripts are not exposed as model tools. `services/orchestrator/app/skill_script_gateway.py` is the fail-closed execution boundary. A request must carry a router-approved task/project scope and the exact chain `agent_worker -> tool_policy -> local_agent`; the gateway resolves the script only from the manifest and never starts a subprocess, opens a network connection, or writes a file itself.

The gateway enforces:

- exact manifest script names and supported execution routes;
- capability intersection across role, task, global policy, and the selected skill;
- repository-declared command argv (no model-generated shell command), trusted executable categories, bounded timeouts, and output limits;
- workspace-relative paths and evidence-only artifact roots (`docs/`, `artifacts/`, `reports/`);
- explicit project-state compatibility-adapter routing for `project-state.json`;
- declared/approved HTTP(S) targets, metadata/private-target blocking, credential-bearing URL rejection, and redirect evidence validation;
- server-side approval verification bound to the exact action hash. A client `approved=true` flag is never authoritative;
- redaction of authorization headers, cookies, tokens, passwords, and private keys before trace/evidence persistence.

Execution uses the existing Local Agent preview/run endpoints through `HttpLocalAgentExecutionClient`. Compatibility-view updates use the existing database-backed adapter and do not execute a helper script. Phase 10C tests cover gateway provenance, least privilege, workspace and network boundaries, approval requirements, timeout behavior, redirect rejection, compatibility routing, untrusted scripts, and secret redaction.
### Explicit task-plan authorization

Command and test runners require an explicitly authorized task plan in addition to the exact repository-declared command tuple. The worker/task planner must set `task_plan_authorized` after deriving the command from trusted skill metadata or an authorized task plan; model-supplied `declared_commands` alone are insufficient. The effective decision remains the intersection of role, task, global, skill, and Local Agent risk policy.
## Phase 10D skill-aware execution validation

Phase 10D validates the routing and worker-context contract against five deterministic scenarios. The scenarios use the real `SkillRouter`, `SkillContextLoader`, `effective_tool_permissions`, quality-gate evaluator, and SQLite task persistence; they do not fabricate a second workflow engine or inject every skill into every task.

| Scenario | Objective class | Relevant project skills | Explicitly excluded examples | Result |
| --- | --- | --- | --- | --- |
| A | New full-stack application with authentication | Analysis, UI, frontend, backend, database, API, auth, application security, testing, QA, final review | Deployment unless requested | PASS |
| B | Backend transaction/migration defect | Analysis, backend, database, testing, QA, final review | UI, frontend, deployment | PASS |
| C | Frontend accessibility improvement | UI, frontend, testing (with contextual QA/final review) | Backend, database, auth, application security, deployment | PASS |
| D | Authentication/security repair | Auth, application security, testing, QA, final review | UI, frontend, database, deployment | PASS |
| E | Release validation | Testing, QA, deployment, final review | UI, frontend, backend, database architecture | PASS |

The persisted trace is available at `reports/phase10d-skill-execution-trace.json`. It contains 25 task records with the task role, selected skills, loaded documents/references, effective tools, gate results, and the `skill_route` event persisted in `agent_tasks.skill_trace_json`. Each task loads only selected `SKILL.md` files and at most the explicitly requested declared reference; the loader enforces byte and item bounds. Initial quality-gate evaluation with missing evidence is blocked, while the deterministic evidence fixture passes the required gates.

This validation proves skill-aware routing, scoped context construction, least-privilege calculation, evidence gates, and trace persistence. It does not claim that a live Model Gateway/Agent Worker has executed model calls; binding this context contract into a production worker remains the next runtime integration blocker.