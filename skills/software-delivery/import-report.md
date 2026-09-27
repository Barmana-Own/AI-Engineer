# Phase 10A Skill Import Report

| Field | Value |
| --- | --- |
| Gregorian date | 2026-09-22 |
| Jalali date | 1405-06-31 |
| Registry | `ai-engineer-software-delivery` |
| State authority | `orchestrator_database` |
| Activation policy | `router_only` |
| Live agent connection | disabled for Phase 10A |
| Outer-package normalization | `12-ullstack-final-review` → `12-fullstack-final-review` |

## Inventory

| Skill | Purpose | Risk | Scripts / safety classes | References | Expected outputs | Stage assumptions |
| --- | --- | --- | --- | ---: | --- | --- |
| `api-integration` | Define stable API contracts and connect real frontend, backend, persistence, and error flows. | high | scan_production_mocks.py [PURE_VALIDATOR]<br>validate_project_state.py [PURE_VALIDATOR]<br>validate_stage06_artifacts.py [COMMAND_RUNNER, PURE_VALIDATOR] | 8 | API contract; OpenAPI document; integration adapters; contract tests; smoke evidence | depends on: backend-architecture, database-architecture |
| `application-security` | Perform defensive threat modeling, vulnerability review, hardening, and security regression verification. | critical | security_pattern_scan.py [PURE_VALIDATOR, ARTIFACT_WRITER]<br>security_preflight.py [COMMAND_RUNNER, ARTIFACT_WRITER]<br>update_project_state.py [ARTIFACT_WRITER]<br>validate_security_artifacts.py [PURE_VALIDATOR] | 18 | threat model; findings; hardening changes; security tests; residual risk register | depends on: authentication-authorization |
| `authentication-authorization` | Implement and verify identity, sessions, RBAC/ABAC, ownership isolation, and abuse controls. | critical | auth_security_audit.py [PURE_VALIDATOR, ARTIFACT_WRITER]<br>validate_stage07_evidence.py [PURE_VALIDATOR] | 14 | auth implementation; authorization matrix; session lifecycle; negative tests; audit evidence | depends on: api-integration |
| `backend-architecture` | Build and verify production-grade backend boundaries, validation, error handling, and application services. | high | validate_stage04.py [PURE_VALIDATOR, ARTIFACT_WRITER] | 13 | backend modules; application services; validation model; unit tests; configuration contract | depends on: frontend-architecture |
| `database-architecture` | Design durable relational persistence, safe migrations, constraints, indexes, and repository adapters. | critical | migration_risk_scan.py [PURE_VALIDATOR]<br>validate_project_state.py [PURE_VALIDATOR]<br>validate_stage_artifacts.py [PURE_VALIDATOR] | 9 | schema; migrations; constraints; indexes; repository adapters; migration evidence | depends on: backend-architecture |
| `deployment-production` | Prepare production builds, configuration, health checks, migration rollout, operations, and rollback evidence. | critical | release_manifest.py [READ_ONLY_INSPECTOR, COMMAND_RUNNER, ARTIFACT_WRITER]<br>self_test.py [TEST_RUNNER, COMMAND_RUNNER, NETWORK_CHECK, ARTIFACT_WRITER]<br>smoke_http.py [NETWORK_CHECK, ARTIFACT_WRITER]<br>stage11_preflight.py [READ_ONLY_INSPECTOR, COMMAND_RUNNER, TEST_RUNNER, ARTIFACT_WRITER]<br>validate_evidence.py [PURE_VALIDATOR] | 7 | production build; deployment configuration; health evidence; operations runbook; rollback plan | depends on: qa-debugging |
| `design-system-ui-architecture` | Convert validated requirements into traceable UI architecture, design-system contracts, responsive rules, and accessibility requirements. | medium | bootstrap_stage02.py [ARTIFACT_WRITER]<br>update_project_state.py [ARTIFACT_WRITER]<br>validate_stage02.py [PURE_VALIDATOR, ARTIFACT_WRITER] | 15 | UI architecture; design tokens; screen inventory; state matrix; accessibility rules | depends on: project-analysis-prompt-engineering |
| `frontend-architecture` | Implement and verify a maintainable production frontend against an approved UI architecture and typed API boundary. | medium | frontend_quality_gate.py [COMMAND_RUNNER, TEST_RUNNER, ARTIFACT_WRITER] | 6 | frontend source; typed client boundary; frontend tests; build evidence | depends on: design-system-ui-architecture |
| `fullstack-final-review` | Perform an independent final release audit, repair gate, traceability review, and release hygiene validation. | critical | build_release_manifest.py [READ_ONLY_INSPECTOR, ARTIFACT_WRITER]<br>discover_project.py [READ_ONLY_INSPECTOR, COMMAND_RUNNER, ARTIFACT_WRITER]<br>package_release.py [READ_ONLY_INSPECTOR, ARTIFACT_WRITER]<br>review_state.py [ARTIFACT_WRITER]<br>run_check.py [COMMAND_RUNNER, ARTIFACT_WRITER]<br>scan_release_hygiene.py [READ_ONLY_INSPECTOR, COMMAND_RUNNER, ARTIFACT_WRITER]<br>validate_final_gate.py [PURE_VALIDATOR, ARTIFACT_WRITER] | 19 | final review; traceability matrix; release manifest; hygiene evidence; release verdict | depends on: deployment-production |
| `project-analysis-prompt-engineering` | Turn a software idea or existing brief into validated, traceable product requirements and a Stage 02 handoff. | medium | bootstrap_stage01.py [ARTIFACT_WRITER]<br>update_project_state.py [ARTIFACT_WRITER]<br>validate_stage01.py [PURE_VALIDATOR, ARTIFACT_WRITER] | 17 | project brief; requirements specification; scope baseline; risk register; stage handoff | depends on: none |
| `qa-debugging` | Exercise release candidates, reproduce defects, perform root-cause analysis, and verify regression fixes. | high | update_project_state.py [ARTIFACT_WRITER]<br>validate_stage10_artifacts.py [PURE_VALIDATOR] | 12 | QA checklist; defect reports; root-cause records; regression evidence; known-issues report | depends on: software-testing |
| `software-testing` | Create risk-based automated verification across unit, integration, contract, authorization, frontend, and end-to-end boundaries. | high | detect_test_stack.py [PURE_VALIDATOR, ARTIFACT_WRITER]<br>validate_stage09_evidence.py [PURE_VALIDATOR] | 10 | test plan; automated tests; fixtures; test results; coverage gaps | depends on: application-security |

## Safety and state compatibility

- The original ``SKILL.md``, ``agents/openai.yaml``, scripts, references, and assets are preserved under ``skills/software-delivery/<skill-id>/``.
- ``allow_implicit_invocation`` is retained for audit visibility only; the registry always requires an explicit router decision plus task, role, and project context.
- Script execution is classified but not exposed as a model tool. The declared boundary is Agent Worker → Tool Policy → Local Agent with workspace, command, network, timeout, output, and approval controls.
- The Orchestrator database remains authoritative. Any skill ``project-state.json`` interaction is compatibility-view-only and cannot create or replace execution state.
- No skill was connected to live agents or a global Stage 01–12 pipeline in this phase.

## Static validation

- 36 bundled Python scripts compile successfully using Python 3.11 without executing them or writing bytecode.
- 12 canonical IDs are unique and all manifest-declared files exist.
- One upstream syntax defect in ``authentication-authorization/scripts/auth_security_audit.py`` was corrected minimally (nested f-string quote); the correction is backed up and recorded as a compatibility fix.
