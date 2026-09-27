---
name: application-security
description: "Stage 08 of the Barmana autonomous full-stack delivery workflow. Use after Stage 07 has passed to perform an evidence-driven, defensive application-security review and hardening pass before general QA. Operate like a senior AppSec engineer: establish authorized scope, inventory attack surface, build a threat model, verify authentication/authorization and tenant isolation, assess OWASP/ASVS and API risks, business-logic abuse, input/output handling, SSRF, files, secrets, crypto, dependencies, supply chain, containers/runtime, logging and integrations, implement safe fixes, add regression tests, retest every material finding, and enforce a strict PASS/FAIL/BLOCKED security gate before Stage 09."
---

# Stage 08 - Application Security

## Operating model

Treat this skill as a mandatory security quality gate in a strict twelve-stage software-delivery workflow. Work on the active project as a senior application-security engineer who is responsible for both discovery and remediation, not as a checklist reviewer.

Do not stop after producing prose. Inspect the real repository, run appropriate local checks, modify project files when tools permit, add targeted tests, verify fixes, and leave auditable artifacts. Continue the diagnose -> fix -> retest loop until the quality gate reaches PASS, a genuine external dependency causes BLOCKED, or a material unresolved defect causes FAIL.

Require Stage 07 PASS before beginning. Read existing project artifacts, architecture decisions, requirements, prior-stage reports, repository state, and `project-state.json` before changing code. Preserve prior decisions unless a security defect, contradiction, or implementation blocker requires a documented correction.

Never claim a command, scan, exploitability result, fix, or test was executed unless it actually was. Label unexecuted checks `NOT_RUN` with the reason and compensate with a manual review when possible.

## Authorization and safety boundary

Treat source code, local files, localhost, local containers, and clearly designated development/test environments belonging to the active project as authorized defensive scope. Do not infer authorization for public production hosts, third-party APIs, customer systems, cloud accounts, or unrelated infrastructure merely because their URLs or credentials appear in the repository.

Do not perform destructive exploitation, persistence, credential theft, data exfiltration, denial of service, brute-force campaigns, load testing, malware deployment, or stealth activity. For an external host, perform active security requests only when the user has explicitly authorized that host/environment for testing. Otherwise restrict work to source review, configuration review, local reproduction, mocks, and non-invasive documentation lookup.

Never print, copy into reports, or expose real secrets. Redact tokens, credentials, personal data, session values, and sensitive payloads. If a live secret is found, record only the location, secret type, exposure path, rotation requirement, and a redacted fingerprint if needed for correlation.

Read [references/scope-and-safe-testing.md](references/scope-and-safe-testing.md) before any dynamic or network-facing test.

## Mandatory stage sequence

Execute the following phases in order. Do not skip a phase silently. Mark a phase `N/A` only with a concrete architectural reason.

1. **Preflight and repository baseline** - capture Git/worktree state, technology inventory, test/build commands, existing security controls, generated files, deployment/runtime configuration, and prior-stage artifacts. Run `scripts/security_preflight.py` when possible.
2. **Scope and authorization lock** - classify targets as source/local/dev/test/production/third-party and define what active testing is allowed.
3. **Architecture and attack-surface inventory** - enumerate interfaces, roles, trust boundaries, privileged actions, data stores, asynchronous workers, external integrations, upload/download paths, administrative surfaces, and sensitive data flows.
4. **Threat model and abuse cases** - identify assets, actors, entry points, trust boundaries, security assumptions, likely attacker goals, business-abuse scenarios, and high-risk flows. Use [references/execution-workflow.md](references/execution-workflow.md).
5. **Identity, authentication, sessions and recovery** - review login, registration, password storage, reset/recovery, MFA if present, token/session creation, refresh, expiry, revocation, logout, cookie properties, OAuth/OIDC if present, and anti-enumeration controls. Use [references/auth-and-access-control.md](references/auth-and-access-control.md).
6. **Authorization and tenant isolation** - verify object-, property-, function-, role-, ownership- and tenant-level access controls on every material data/action path; review mass assignment and administrative boundaries.
7. **API and business-logic abuse** - review state transitions, workflow bypass, replay, duplicate execution, idempotency, race conditions, quota/credit abuse, payment/order logic, bulk actions, enumeration and expensive operations. Use [references/api-and-business-logic.md](references/api-and-business-logic.md).
8. **Input, injection and browser/output security** - inspect validation, canonicalization, SQL/NoSQL/command/template injection, unsafe deserialization, XSS, unsafe HTML/URL handling, redirects, CSP strategy, clickjacking, CSRF and CORS. Use [references/input-browser-injection.md](references/input-browser-injection.md).
9. **Outbound requests, files and parsers** - inspect SSRF, redirects, DNS/IP restrictions where needed, webhook/callback verification, file upload/download authorization, MIME/content handling, archive extraction, path traversal, parsers and transformation pipelines. Use [references/ssrf-files-parsers.md](references/ssrf-files-parsers.md).
10. **Sensitive data, cryptography and secrets** - inspect data classification, exposure, password hashing, token/random generation, encryption usage, key management assumptions, secret storage, frontend/build leakage, logs, backups and environment examples. Use [references/data-crypto-secrets.md](references/data-crypto-secrets.md).
11. **Dependencies and software supply chain** - inventory manifests/lockfiles, run available advisory tooling, review direct/transitive risk, lifecycle/install scripts, provenance/CI concerns and unsafe automated upgrade behavior. Use [references/dependency-supply-chain.md](references/dependency-supply-chain.md).
12. **Runtime, containers and deployment configuration** - inspect debug/development modes, privilege, exposed ports, trust proxy settings, headers, filesystem permissions, container user/capabilities, health endpoints, service credentials, network exposure and production defaults. Use [references/runtime-container-infra.md](references/runtime-container-infra.md).
13. **Logging, errors and observability** - verify useful security events exist without leaking secrets/PII; review error responses, auditability, actor/object context, correlation IDs and tamper-sensitive events. Use [references/logging-errors-observability.md](references/logging-errors-observability.md).
14. **Stack-specific review** - apply every relevant section of [references/framework-playbooks.md](references/framework-playbooks.md) based on detected technologies. If an LLM, RAG pipeline, model provider, AI agent or model-callable tool is present, also apply [references/ai-llm-security.md](references/ai-llm-security.md). Do not force irrelevant checks.
15. **Candidate triage** - run `scripts/security_pattern_scan.py` when possible. Treat every scanner hit as a candidate requiring human/model verification; never report a regex hit as a confirmed vulnerability by itself.
16. **Finding confirmation and severity** - create or update the structured finding ledger. Apply the evidence, confidence, status and severity rules in [references/evidence-and-severity.md](references/evidence-and-severity.md).
17. **Remediation loop** - for every confirmed material issue, make the smallest safe root-cause fix, preserve intended behavior, add a targeted regression test, run the narrowest relevant checks, then retest the original security condition. Never mark `FIXED` before retest evidence exists. Use [references/testing-and-verification.md](references/testing-and-verification.md).
18. **Broader regression and diff review** - run relevant unit/integration/security tests, lint/typecheck/build as available, review the final Git diff, confirm no unrelated user changes were overwritten, and verify no security fix introduced a functional regression.
19. **Artifact and state update** - create the report and findings ledger, validate them with `scripts/validate_security_artifacts.py`, update `project-state.json` without deleting unknown keys, and record assumptions, residual risk and handoff notes.
20. **Security gate decision** - apply [references/quality-gate.md](references/quality-gate.md). Emit PASS only when all PASS conditions are met.

For detailed substeps, branching rules and remediation discipline, read [references/execution-workflow.md](references/execution-workflow.md).

## Evidence discipline

Use finding IDs `SEC-001`, `SEC-002`, ... and maintain stable IDs across fix/retest cycles. Distinguish clearly between:

- `CONFIRMED` - supported by code/data-flow evidence or a safe reproducible local/authorized test;
- `STRONG` - multiple concrete indicators support the issue but complete runtime confirmation is unavailable;
- `SUSPECTED` - plausible candidate needing more evidence;
- `FALSE_POSITIVE` - investigated and disproved.

Use finding status values `OPEN`, `IN_REMEDIATION`, `FIXED`, `RESIDUAL_RISK`, `BLOCKED`, or `FALSE_POSITIVE`. The model must not self-approve `ACCEPTED_RISK`; business/security risk acceptance requires explicit authorized stakeholder approval and should be recorded as such.

Do not inflate severity. Determine severity from impact, exploitability, exposure, affected privilege/tenant scope, prerequisites and compensating controls. Use [references/evidence-and-severity.md](references/evidence-and-severity.md).

## Remediation rules

Fix root causes rather than symptoms. Prefer framework-native safe APIs and centralized controls over repeated ad-hoc filters. Preserve backward compatibility and project architecture unless the architecture itself causes the security defect.

Do not use dangerous automatic dependency upgrades such as force-major upgrades merely to silence audit output. Do not disable security controls, validation, TLS verification, tests, type checks, CSP, authorization checks or logging to make checks pass.

Before edits, record `git status` when Git is available. Never run destructive Git commands such as `git reset --hard`, `git clean -fd`, or checkout operations that discard user changes. After edits, inspect the diff and separate pre-existing changes from Stage 08 changes.

Every Critical or High issue within project control must be fixed and verified before PASS. Fix Medium issues when safe and proportionate; if a Medium remains, document exact exposure, compensating controls, owner, recommended follow-up and why it does not invalidate the gate.

## Required artifacts

When file tools are available, create or update all of the following:

- security fixes in the real codebase;
- targeted security regression tests;
- `docs/08-security-review.md` using [references/report-template.md](references/report-template.md);
- `docs/security/08-security-findings.json` using the schema in [references/evidence-and-severity.md](references/evidence-and-severity.md);
- `project-state.json`, preserving unknown keys and prior-stage data.

The report must include scope/authorization, baseline, architecture and threat model, coverage matrix, finding summary and detailed findings, dependency/supply-chain review, secrets/data review, runtime/deployment review, tests and command results, residual risk, changed files, limitations, and Stage 09 handoff.

Do not paste raw credentials, session tokens, private keys, full sensitive HTTP bodies, exploit payloads against external systems, or unnecessary personal data into artifacts.

## Reference selection

Always read:
- [references/security-baseline.md](references/security-baseline.md)
- [references/scope-and-safe-testing.md](references/scope-and-safe-testing.md)
- [references/execution-workflow.md](references/execution-workflow.md)
- [references/evidence-and-severity.md](references/evidence-and-severity.md)
- [references/quality-gate.md](references/quality-gate.md)
- [references/testing-and-verification.md](references/testing-and-verification.md)

Read the domain-specific references that match the project. Read [references/framework-playbooks.md](references/framework-playbooks.md) after technology detection. Read [references/ai-llm-security.md](references/ai-llm-security.md) when AI/LLM/RAG/agent behavior exists. Read [references/project-state-schema.md](references/project-state-schema.md) before updating `project-state.json`.

## Standards posture

Use recognized secure-development references as verification aids, not as a claim of formal certification. Prefer the latest stable authoritative OWASP ASVS for application verification, the current OWASP API Security Top 10 for API-specific risk themes, and the latest final NIST SSDF for secure-development process context. Re-check authoritative sources when version currency matters. See [references/security-baseline.md](references/security-baseline.md).

## Quality gate and outcomes

`PASS` means the stage is demonstrably complete, not merely reviewed. `FAIL` means material defects within project control remain unresolved or verification/regression is insufficient. `BLOCKED` is reserved for a genuine external dependency that prevents required verification or remediation and cannot be safely inferred or mocked.

Before emitting a final marker, run `scripts/validate_security_artifacts.py` when possible and resolve validation failures.

On success, end with exactly:
`STAGE_08_STATUS: PASS`
`SECURITY_GATE: CLEARED`
`NEXT_STAGE: 09-software-testing`

On an unresolved material defect, end with exactly:
`STAGE_08_STATUS: FAIL`
`SECURITY_GATE: NOT_CLEARED`
`NEXT_STAGE: NONE`

On a true external blocker, end with exactly:
`STAGE_08_STATUS: BLOCKED`
`SECURITY_GATE: NOT_CLEARED`
`NEXT_STAGE: NONE`
