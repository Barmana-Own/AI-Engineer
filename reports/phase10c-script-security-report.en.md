# Phase 10C — Skill Script Execution Security Report

| Field | Value |
| --- | --- |
| Project | AI-Engineer |
| Phase | 10C — Harden Skill Script Execution |
| Language | English |
| Gregorian date | 2026-09-22 |
| Jalali date | 1405-06-31 |
| Status | IMPLEMENTED WITH KNOWN RUNTIME INTEGRATION LIMITATION |

## SCRIPT SECURITY MODEL

`services/orchestrator/app/skill_script_gateway.py` is the single policy boundary for imported skill helpers. A request is accepted only when it declares the exact manifest skill/script, the required execution chain (`agent_worker` → `tool_policy` → `local_agent`), an approved router scope, and an effective capability intersection. The gateway performs no direct subprocess, socket, or unrestricted file-write operation.

The gateway resolves only manifest-declared script names under the selected skill's `scripts/` directory. Path separators, traversal, untrusted skill paths, and missing files are rejected. External `allow_implicit_invocation` metadata is not authoritative.

## COMMAND EXECUTION POLICY

Commands are accepted only when the complete argument tuple matches a repository-declared command plan. The policy also requires a trusted executable category, rejects shell/control metacharacters and traversal, confines path arguments to the workspace/allowed roots, applies role/task/global capability intersection, and bounds timeout and output size. A command runner in a reviewer skill cannot grant the reviewer write or unrestricted shell access.

The Local Agent adapter receives the validated plan only after the gateway policy decision. Its legacy `approved` field is passed only as a compatibility signal after server-side approval; it is never treated as the source of authorization.

## NETWORK POLICY

Network checks require an absolute HTTP(S) URL that matches a declared project target or an explicitly approved deployment target. Credential-bearing URL userinfo and sensitive query parameters are rejected. Cloud metadata hosts and undeclared private/reserved targets are blocked. Localhost/dev health checks work only when explicitly declared. Returned `url`/`response_url` evidence is checked for undeclared redirects and rejected when it leaves the approved target set.

The gateway cannot guarantee redirect visibility when an external helper omits the final response URL; this remains a documented limitation for future helper adapters.

## WORKSPACE POLICY

Resolved paths must remain under configured allowed roots. Traversal is rejected before normalization, symlink resolution is applied, and artifact writes are limited to `docs/`, `artifacts/`, or `reports/`. `project-state.json` is available only through the compatibility-adapter route, so the database remains authoritative. Artifact results are bounded and safely serialized.

## SECRET REDACTION

Evidence, headers, stdout, stderr, and returned mappings are redacted and size-limited before persistence/return. Bearer/Basic credentials, authorization/cookie headers, token/API-key/password/secret/private-key fields, private-key blocks, and `.env`-style values are removed. Redaction is tested independently and through a successful Local Agent execution.

## APPROVAL INTEGRATION

High/critical-risk scripts and network checks require an injected server-side `ApprovalVerifier` and an exact canonical action hash. `client_approved=true` is ignored. Missing, expired, rejected, consumed, or mismatched approvals fail closed. The gateway exposes the approval hook and single-action hash contract; full persisted ApprovalRequest storage and live worker wiring remain outside this phase and must be connected before production autonomy is enabled.

## TEST RESULTS

| Validation | Result |
| --- | --- |
| Targeted `test_skill_script_gateway.py` | PASS — 20 passed |
| Orchestrator suite | PASS — 93 passed, 10 subtests passed |
| Model Gateway suite | PASS — 25 passed |
| Local Agent Python compile | PASS — 15 modules compiled; no Local Agent pytest suite present |
| Changed Python compile | PASS |
| `git diff --check` | PASS — no whitespace errors; existing line-ending warnings only |
| Skill helper inventory compile (Phase 10A baseline) | PASS — 36 scripts compiled without execution |
| Node builds | NOT_RUN — outside Phase 10C scope; no frontend files changed |

## FILES AND ARTIFACTS

- `services/orchestrator/app/skill_script_gateway.py`
- `services/orchestrator/app/skill_registry.py`
- `services/orchestrator/tests/test_skill_script_gateway.py`
- `skills/software-delivery/integration-policy.json`
- `docs/skills-routing.md`
- `skills/software-delivery/README.md`

Verified backups were created before edits. The latest gateway cleanup backup is `F:\phase9work\backups\phase10c-gateway-cleanup-20260922-144748.zip` with SHA-256 `4FA250CBF92F7B63BBA37210F7A7BB918BABD31F503885F9E531F810EAD06C51`.

## LIMITATIONS

The policy gateway is implemented and tested, but this repository does not yet expose a dedicated live Agent Worker runtime that invokes every imported helper through it. The gateway therefore enforces the intended chain at its API boundary and provides Local Agent/compatibility adapters; wiring it into the live worker remains required. The existing Local Agent legacy boolean remains for backward compatibility, but cannot authorize a request through this gateway.
## TASK-PLAN AUTHORIZATION

Command and test runners require `task_plan_authorized=true` from the worker/task planner. A model cannot self-authorize by supplying `declared_commands`; the command must originate from a trusted repository/skill definition or an explicitly authorized task plan.
High-risk compatibility-adapter updates are also approval-gated; a critical `project-state.json` update cannot bypass the server-side verifier.