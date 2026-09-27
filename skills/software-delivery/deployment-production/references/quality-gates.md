# Stage 11 Quality Gates and Evidence Policy

## Table of contents

1. Gate philosophy
2. Status model
3. Severity model
4. Evidence rules
5. Mandatory gates
6. N/A policy
7. Warning policy
8. PASS algorithm
9. BLOCKED algorithm
10. FAIL algorithm
11. Evidence examples
12. Anti-patterns

## 1. Gate philosophy

A gate is a release decision backed by evidence. Do not treat a checklist item as complete merely because a file with a plausible name exists.

Every applicable gate needs:

- a status;
- a concise finding;
- concrete evidence references;
- commands/checks actually executed when tools permit;
- remediation notes for failures;
- applicability rationale if `N_A` is used.

## 2. Status model

Use these evidence-ledger statuses:

- `PASS`: control is applicable and verified.
- `FAIL`: control is applicable and failed.
- `N_A`: control is genuinely not applicable; include a specific rationale.
- `BLOCKED`: verification or required implementation depends on an unavailable external dependency.

Do not use `WARN` as the final state for a mandatory gate. Put warnings inside findings, then decide whether the gate still passes or fails.

Final Stage 11 status:

- `PASS` only if every mandatory gate is `PASS` or justified `N_A`, there is no blocked mandatory verification required by the project, and no P0/P1 blocker remains.
- `BLOCKED` if one or more mandatory outcomes cannot be completed because of a true external blocker and no safe substitute exists.
- `FAIL` if a mandatory technical gate remains failed after remediation or stage safety forbids proceeding.

## 3. Severity model

Use severity for findings, not for gate status:

- `P0`: active compromise, likely irreversible data loss, destructive production action already occurring incorrectly, or immediate severe safety/security risk. Stop mutating work and stabilize first.
- `P1`: release blocker with high likelihood/impact: embedded production secret, broken auth/TLS, unrecoverable destructive migration, failed production build, public database exposure, no viable recovery for a high-risk data change.
- `P2`: important production defect that should be fixed before release unless explicitly accepted by an authorized risk process: missing readiness behavior, incomplete alerting for a critical path, unpinned high-risk deployment action, untested restore in a mature critical system.
- `P3`: lower-risk hardening/maintainability improvement that does not invalidate Stage 11 PASS when documented and justified.

Do not downgrade severity just to achieve PASS.

## 4. Evidence rules

Strong evidence includes:

- command + exit code/output summary;
- generated artifact hash/digest;
- test report;
- HTTP response from an actual smoke target;
- target deployment/revision identifier;
- migration status from the actual database/tool;
- scanner report;
- restore drill result;
- config validation failure/success demonstration;
- CI workflow file plus successful pipeline result when available;
- log/metric/trace sample produced by the running service.

Weak evidence that cannot stand alone:

- prose saying "configured";
- a TODO list;
- code not executed when execution was available;
- an unverified screenshot without target identity;
- a Dockerfile that was never built;
- a backup script that was never run or reviewed;
- a health endpoint file without an HTTP test;
- an environment template without startup validation.

Evidence must not contain secret values.

## 5. Mandatory gates

### G00_PRECONDITIONS

Require:

- Stage 10 verifiably passed;
- no unresolved P0/P1 Stage 10 release blocker;
- project root/source identity established.

Fail if Stage 10 is known failed or release blockers remain. Block if authoritative Stage 10 state is required but inaccessible.

### G01_RELEASE_BASELINE

Require:

- release-relevant stack/dependency inventory;
- source commit/ref or equivalent identity;
- dirty-tree state known when Git is used;
- target operating model identified or explicitly provider-neutral;
- release risk map started;
- evidence ledger initialized.

### G02_DETERMINISTIC_BUILD

Require all applicable deployables to:

- use locked/pinned dependency resolution where ecosystem supports it;
- install/build from declared inputs;
- avoid development-only startup in production;
- successfully build using production commands when executable tools are available;
- identify artifact/output.

Fail on a reproducible build error, missing required lock mechanism, or hidden local-only dependency that remains unresolved.

### G03_RUNTIME_PACKAGING

Require target-appropriate packaging. For containers, verify build/start, runtime command, privilege model, secret exclusion, graceful shutdown expectations, and persistence boundaries.

`N_A` is valid when the delivery target legitimately does not use a server runtime/container, for example a pure static artifact, but still verify target-native packaging.

### G04_CONFIG_AND_SECRETS

Require:

- configuration inventory;
- startup validation for critical values;
- safe example/template;
- no real secret in source/artifact/examples/evidence;
- production-insecure defaults eliminated or guarded;
- secret source/ownership defined.

Any confirmed live credential committed/exposed is at least P1 until rotated/revoked and removed from relevant history/systems as appropriate.

### G05_DATABASE_AND_DATA

Require when stateful data exists:

- migration execution model;
- rollout compatibility analysis;
- destructive-change controls;
- backup/recovery prerequisite where needed;
- worker/queue/cache/storage compatibility;
- migration validation when executable.

`N_A` only for projects with no durable/stateful data requiring release coordination.

### G06_EDGE_AND_NETWORK

Require:

- TLS/entrypoint model;
- proxy trust behavior;
- CORS and public exposure review;
- request/timeouts/upload limits as relevant;
- internal services not unintentionally public;
- production-like edge validation when available.

### G07_CI_CD_AND_PROMOTION

Require:

- pre-release validation in CI or an equivalent controlled release process;
- deploy blocked on failed validation;
- deploy credentials isolated/least-privilege;
- immutable or source-identical promotion strategy;
- production authorization/protection rule;
- concurrent deploy behavior handled.

For very small/manual systems, a fully automated CD pipeline may be `N_A`, but the controlled release process must still be reproducible and evidence-backed. Do not use `N_A` merely to skip CI when the repository already depends on CI.

### G08_SUPPLY_CHAIN_SECURITY

Require available ecosystem-appropriate:

- secret scan;
- dependency vulnerability review;
- production artifact/image review or scan when supported;
- external CI dependency pinning review;
- artifact checksum/digest;
- SBOM/provenance when required or reasonably supported.

Unavailable tooling must be recorded. A critical/high exploitable finding may block PASS.

### G09_OBSERVABILITY

Require:

- useful structured logs or platform-equivalent logs;
- secret/PII redaction policy;
- health/readiness semantics;
- meaningful error/latency/resource/dependency visibility for critical paths;
- alerting/ownership expectations;
- production diagnosis path in the runbook.

### G10_BACKUP_RESTORE

Require for durable state:

- backup ownership/mechanism;
- retention/security;
- RPO/RTO or explicit recovery expectation;
- documented restore procedure;
- restore verification strategy, preferably an executed non-production restore when possible.

`N_A` only when there is genuinely no persistent state to restore.

### G11_RELEASE_STRATEGY

Require:

- selected rollout strategy or target-native equivalent;
- predeploy checks;
- health acceptance threshold;
- rollback/roll-forward trigger;
- application/config/schema rollback compatibility analysis;
- incident recovery steps.

### G12_PRODUCTION_LIKE_VALIDATION

Require:

- exact release artifact built;
- production-equivalent startup;
- applicable smoke checks passed;
- relevant services/workers/dependencies validated;
- deployment-related code changes covered by regression checks.

If execution tools are available and this was not run, the gate fails. If the environment cannot be constructed only because of a true external dependency, classify specifically rather than pretending success.

### G13_DEPLOYMENT_TRUTH

Require one of:

- `PERFORMED`: real external deployment actually occurred with authorization and evidence;
- `NOT_PERFORMED`: real deployment did not occur and all docs/state say so consistently.

Fail on invented deployment claims, fabricated URLs, or mismatched artifact identity.

### G14_EVIDENCE_AND_HANDOFF

Require:

- release manifest;
- evidence ledger;
- deployment document;
- operations runbook;
- release report;
- project-state update;
- precise Stage 12 handoff.

## 6. N/A policy

`N_A` requires all of:

1. the control truly does not apply to this architecture;
2. the rationale names the architectural fact that makes it irrelevant;
3. no equivalent control is being skipped;
4. the reviewer could reproduce the applicability decision.

Bad rationale: "Not needed."

Good rationale: "No durable store exists; this is a static client bundle served from immutable CDN storage and no user-generated state is persisted by this repository, so database migration and backup gates are N_A; artifact rollback remains covered by G11."

## 7. Warning policy

A warning must include:

- risk statement;
- severity;
- whether release is affected;
- compensating control if any;
- owner/next action if not fixed;
- rationale for allowing PASS.

Warnings with unknown impact are not automatically harmless. Investigate them.

## 8. PASS algorithm

Before PASS:

1. Run evidence validation.
2. Confirm no gate is `FAIL` or `BLOCKED`.
3. Review every `N_A` rationale.
4. Review every P0/P1 finding; count must be zero unresolved.
5. Confirm all P2 findings are fixed or formally justified without contradicting project policy.
6. Confirm release candidate source/artifact identity.
7. Confirm smoke evidence belongs to that artifact/version.
8. Confirm real-deployment status is truthful.
9. Confirm project state and Stage 12 handoff match the evidence ledger.

## 9. BLOCKED algorithm

Use BLOCKED only when:

- a mandatory requirement cannot be completed without unavailable external access/approval/fact;
- no safe provider-neutral or local substitute can satisfy the gate;
- the blocker is recorded with exactly what is needed to continue;
- all work not dependent on that blocker has still been completed.

Do not block merely because deployment credentials are absent if a real external deployment is optional and all production-readiness work can still pass.

## 10. FAIL algorithm

Use FAIL when:

- technical validation still fails after remediation;
- proceeding would require weakening security;
- the release candidate cannot be reproduced;
- a release-blocking security/data risk remains;
- required evidence contradicts the claimed release state;
- destructive/unsafe migration risk cannot be made acceptable within scope.

## 11. Evidence examples

Build evidence example:

```json
{
  "gate": "G02_DETERMINISTIC_BUILD",
  "status": "PASS",
  "summary": "API and web production builds succeeded from locked dependencies.",
  "evidence": [
    "cmd:npm ci --ignore-scripts=false -> exit 0",
    "cmd:npm run build -> exit 0",
    "file:dist/server.js",
    "file:web/dist/index.html"
  ]
}
```

Real deployment truth example:

```json
{
  "gate": "G13_DEPLOYMENT_TRUTH",
  "status": "PASS",
  "summary": "External deployment not performed because no authorized target credentials were provided.",
  "evidence": ["deployment_status:NOT_PERFORMED"]
}
```

## 12. Anti-patterns

Never accept these as PASS logic:

- "Dockerfile exists, therefore container gate passes."
- "CI YAML looks correct, therefore deployment is proven."
- "There is a /health route, therefore readiness is complete."
- "Backups are enabled by the cloud provider" without identifying the actual policy/evidence.
- "No secrets found" after only searching for the word `password`.
- "Migration can be rolled back" without checking whether data was destroyed/transformed.
- "Production deployed" when only a local Compose stack ran.
- "Scanner unavailable, so no vulnerabilities detected."
