# Stage 11 Artifact Contracts

## Table of contents

1. Purpose
2. Required paths
3. Evidence ledger schema
4. Release manifest schema
5. Deployment document template
6. Operations runbook template
7. Release report template
8. Project-state update rules
9. Stage 12 handoff contract
10. Command evidence format
11. Sensitive-data rules
12. Consistency checks

## 1. Purpose

Use these contracts to make Stage 11 output machine-checkable and reviewable. Adapt optional fields to the project, but preserve the core semantics.

Do not fabricate evidence to satisfy a schema. Use `null`, `N_A`, `NOT_PERFORMED`, or a clearly described blocker where reality requires it.

## 2. Required paths

Prefer these paths when the repository has no conflicting established convention:

```text
docs/11-deployment.md
docs/11-operations-runbook.md
docs/11-release-report.md
artifacts/stage-11/preflight.json
artifacts/stage-11/release-manifest.json
artifacts/stage-11/evidence.json
project-state.json
```

Do not create duplicate documentation trees if the project already has an established release/runbook location. In that case, update the established files and record their actual paths in the evidence ledger.

## 3. Evidence ledger schema

Use this semantic structure:

```json
{
  "stage": "11-deployment-production",
  "generated_at": "RFC3339 timestamp",
  "source": {
    "commit": "git SHA or null",
    "ref": "branch/tag/ref or null",
    "dirty": false
  },
  "release_candidate": {
    "version": "project version/release id or null",
    "artifact_ids": ["digest/path/id"]
  },
  "deployment": {
    "status": "PERFORMED or NOT_PERFORMED",
    "target": "target id/name or null",
    "url": "verified deployed URL or null"
  },
  "gates": [
    {
      "id": "G00_PRECONDITIONS",
      "status": "PASS",
      "summary": "Concise factual conclusion",
      "evidence": ["command/file/report/reference"],
      "findings": [],
      "rationale": null
    }
  ],
  "residual_risks": [],
  "blockers": [],
  "stage12_handoff": {
    "review_focus": [],
    "known_warnings": [],
    "external_assumptions": []
  }
}
```

All gate IDs `G00` through `G14` defined in `quality-gates.md` must exist exactly once.

Allowed final gate statuses:

- `PASS`
- `FAIL`
- `N_A`
- `BLOCKED`

For `N_A`, set `rationale` to a specific non-empty explanation.

For `FAIL` or `BLOCKED`, include at least one finding or blocker/evidence item explaining why.

### Finding object

Recommended finding shape:

```json
{
  "id": "REL-SEC-001",
  "severity": "P1",
  "title": "Production secret present in tracked config",
  "status": "RESOLVED",
  "evidence": ["file:.env.production:REDACTED", "rotation:confirmed"],
  "remediation": "Removed tracked value, rotated credential, switched runtime to secret store."
}
```

Do not put the secret itself into the object.

## 4. Release manifest schema

Use this semantic structure:

```json
{
  "schema_version": 1,
  "generated_at": "RFC3339 timestamp",
  "source": {
    "commit": "SHA or null",
    "ref": "branch/tag/ref or null",
    "dirty": false
  },
  "release": {
    "version": "release/version id or null",
    "environment": "staging/production/preproduction/etc",
    "deployment_status": "PERFORMED or NOT_PERFORMED",
    "target": "target or null"
  },
  "artifacts": [
    {
      "path": "relative/path",
      "type": "file or directory",
      "sha256": "hex digest",
      "size_bytes": 123
    }
  ],
  "images": [
    {
      "name": "registry/image:tag",
      "digest": "sha256:..."
    }
  ],
  "migrations": {
    "tool": "tool or null",
    "target_version": "version/id or null",
    "status": "PASS/N_A/NOT_RUN/BLOCKED"
  },
  "security": {
    "sbom": "path/id or null",
    "scan_reports": []
  },
  "validation": {
    "evidence_ledger": "artifacts/stage-11/evidence.json",
    "smoke_report": "path or null"
  }
}
```

A directory digest must be deterministic: hash relative paths plus file bytes in sorted order and exclude volatile metadata.

The manifest identifies the release candidate. Regenerate it if an artifact changes.

## 5. Deployment document template

`docs/11-deployment.md` should normally contain:

```markdown
# Stage 11 Deployment

## Release candidate
- Source commit/ref
- Version
- Artifact/image identity
- External deployment status

## Target architecture
- Environment topology
- Public entrypoint/TLS
- Runtime/process model
- Stateful dependencies
- Network/trust boundaries

## Build
- Runtime/toolchain versions
- Locked dependency install
- Build commands
- Build outputs

## Configuration and secrets
- Config source model
- Required key categories
- Startup validation
- Secret source/rotation
- Client-public config boundary

## Database/data rollout
- Migration tool
- Migration order
- Compatibility model
- Backup prerequisite
- Backfill/queue/cache/storage notes

## CI/CD and promotion
- Validation stages
- Artifact build/publish
- Promotion rule
- Production approval
- Deploy identity/permissions

## Edge/TLS/proxy
- TLS termination
- Forwarded-header trust
- CORS
- Limits/timeouts
- Health/metrics exposure

## Observability
- Logs
- Metrics
- Traces
- SLI/SLO or thresholds
- Alerts

## Release strategy
- Rolling/blue-green/canary/recreate
- Predeploy checks
- Acceptance thresholds
- Rollback/roll-forward trigger

## Validation results
- Production-like smoke
- Security scans
- Restore verification
- Real deployment/post-deploy evidence if performed

## Residual risks
- Explicit list with severity/owner/next action
```

Keep facts specific to the repository. Do not paste generic textbook material merely to make the document long.

## 6. Operations runbook template

`docs/11-operations-runbook.md` should normally contain:

```markdown
# Operations Runbook

## Service inventory
## Start/stop/restart
## Health and readiness
## Logs/metrics/traces
## Routine release procedure
## Migration procedure
## Backup procedure
## Restore procedure
## Rollback/roll-forward
## Incident: service unavailable
## Incident: high latency/errors
## Incident: database/migration failure
## Incident: queue/worker failure
## Incident: external dependency outage
## Incident: storage failure
## Incident: secret compromise
## Escalation and ownership
```

For every operational command specify the target/environment guard needed to avoid running it against the wrong system.

Do not include live credentials.

## 7. Release report template

`docs/11-release-report.md` is the reviewer-facing Stage 11 summary. Use:

```markdown
# Stage 11 Release Report

## Outcome
PASS / BLOCKED / FAIL

## Release candidate identity
Source, version, artifact/image digests.

## Work performed
Concrete repository/runtime/pipeline changes.

## Gate summary
Table of G00-G14 with status and strongest evidence.

## Tests and validation executed
Exact high-value commands/checks and outcomes.

## Real deployment truth
PERFORMED or NOT_PERFORMED, target, evidence.

## Findings resolved
Release-significant defects fixed in Stage 11.

## Residual risks and accepted warnings
No hidden warnings.

## Stage 12 handoff
Independent checks the final reviewer should perform.
```

## 8. Project-state update rules

When `project-state.json` exists:

1. Parse it as JSON; do not edit with fragile text replacement.
2. Preserve every unknown top-level and nested key not intentionally changed.
3. Preserve previous completed-stage history.
4. Add/update Stage 11 using the repository's established schema where possible.
5. Record:
   - stage id/name;
   - final status;
   - source/release identity;
   - important artifacts;
   - material decisions;
   - assumptions;
   - resolved significant findings;
   - residual risks;
   - blockers if any;
   - external deployment truth;
   - next stage.
6. Never mark Stage 12 complete from Stage 11.

If no state file exists but the master workflow requires one, create it conservatively and document that it was initialized in Stage 11.

## 9. Stage 12 handoff contract

Stage 12 must receive enough information to independently challenge Stage 11.

Include:

- exact source commit/ref;
- dirty-tree state at validation time;
- exact release version/id;
- artifact paths/digests/image digests;
- build commands;
- migration target/status;
- production-like target used for smoke;
- external deployment status and evidence;
- all P2/P3 residual findings;
- accepted warnings with rationale;
- controls marked `N_A` and why;
- unavailable external validations;
- areas requiring independent final review.

Recommended final-review focus list:

- reproduce clean build;
- verify artifact/source identity;
- inspect unresolved warnings;
- verify no P0/P1 blocker;
- sample security/secret controls;
- sample migration/recovery logic;
- verify smoke evidence belongs to current artifact;
- verify real-deployment claim;
- review production runbook for actionable steps.

## 10. Command evidence format

For high-value commands, store a concise record:

```text
command: npm ci
cwd: /workspace/project
exit_code: 0
result: locked dependency install succeeded
artifact/log: artifacts/stage-11/logs/npm-ci.txt
```

If full logs contain sensitive data, store a redacted summary instead of blindly archiving raw output.

Do not claim exit codes for commands that were not executed.

## 11. Sensitive-data rules

Never store these in Stage 11 artifacts:

- passwords;
- API tokens;
- session/refresh/access tokens;
- private keys;
- cloud secret keys;
- database passwords;
- OTPs;
- authorization headers;
- customer data copied only for evidence.

Use placeholders such as `<REDACTED>` only to describe the category; do not preserve partial secrets unnecessarily.

## 12. Consistency checks

Before PASS verify all documents agree on:

- source commit;
- release version;
- artifact/image identity;
- deployment target;
- deployment performed/not performed;
- migration status;
- gate statuses;
- residual blockers/risks;
- next stage.

A contradiction between evidence ledger, release manifest, runbook, and project state is itself a handoff defect and must be fixed before PASS.
