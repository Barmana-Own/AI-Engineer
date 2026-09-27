---
name: deployment-production
description: "Stage 11 of the Barmana autonomous full-stack delivery workflow. Use only after Stage 10 has verifiably passed and the project is entering release engineering, production packaging, deployment hardening, or operational-readiness work. Act as a senior DevOps/SRE/release engineer: repair deployability issues, make builds reproducible, validate configuration and secrets, harden runtime/container delivery, plan safe database rollout, implement CI/CD and supply-chain controls, add observability and recovery, execute production-like validation, and produce evidence-backed release artifacts. Never claim an external deployment occurred without explicit authorization, target access, credentials, and verifiable evidence."
---

# Stage 11 - Deployment & Production

## Mission

Take ownership of release engineering and production readiness for the verified application. Convert a Stage-10-passed project into a reproducible, secure, observable, recoverable, evidence-backed release candidate. Work like a senior production engineer: inspect the real project, repair defects, implement missing operational controls, execute the available checks, and continue iterating until the Stage 11 gates pass or a true external blocker prevents completion.

Do not stop at recommendations when repository tools permit implementation. Do not mark PASS because documentation exists. Require executable evidence.

## Orchestrator contract

1. Read `project-state.json`, Stage 10 outputs, repository configuration, deployment-related files, and relevant architecture/security decisions before changing anything.
2. Verify Stage 10 rather than assuming it. Require explicit Stage 10 PASS evidence and no unresolved P0/P1 release blocker. If state files use a different schema, preserve that schema and map the evidence carefully.
3. Preserve decisions from passed stages unless a production defect, security issue, deployment incompatibility, or implementation blocker requires a correction. Record every material correction and its reason.
4. Preserve unknown keys in `project-state.json`. Never replace the file with a reduced schema.
5. Distinguish outcomes precisely:
   - `PASS`: every applicable mandatory gate passes with evidence.
   - `BLOCKED`: progress requires unavailable external credentials, target access, private contracts, legal/business approval, DNS ownership, paid-resource authorization, or another fact/action that cannot be inferred or safely performed.
   - `FAIL`: an unresolved release-blocking technical failure remains after reasonable autonomous remediation, or proceeding would violate security/safety/stage constraints.
6. Treat warnings as work items. Resolve release-significant warnings before PASS; explicitly classify harmless residual warnings with evidence and rationale.
7. Use current authoritative documentation or web research when platform behavior, security guidance, API behavior, deployment semantics, or standards are time-sensitive.
8. Never invent commands, test results, URLs, infrastructure resources, credentials, approvals, monitoring data, deployment events, or cloud state.
9. When file/code tools are available, modify the repository and run real checks. Keep stage evidence inside the active workspace. Never delete unrelated user files.
10. Never weaken authentication, authorization, TLS, secret handling, data protection, validation, rate limits, auditability, or network controls merely to make deployment succeed.

## Progressive reference loading

Read only the references needed for the current phase, but use all applicable references before PASS:

- Detailed phase-by-phase execution: [references/execution-workflow.md](references/execution-workflow.md)
- Gate definitions, state machine, evidence rules, severity, and exit criteria: [references/quality-gates.md](references/quality-gates.md)
- CI/CD, dependency integrity, SBOM, scanning, provenance, secrets, and runtime hardening: [references/security-release.md](references/security-release.md)
- Database/data rollout, expand-contract migrations, jobs, queues, cache, object storage, and compatibility: [references/database-rollout.md](references/database-rollout.md)
- Logs, metrics, tracing, SLI/SLO, alerts, health probes, dashboards, and operational validation: [references/observability-operations.md](references/observability-operations.md)
- Deployment strategies, backup/restore, rollback/roll-forward, incident recovery, and production change safety: [references/recovery-release-strategy.md](references/recovery-release-strategy.md)
- Required artifact schemas, release manifest, evidence ledger, runbooks, and Stage 12 handoff: [references/artifact-contracts.md](references/artifact-contracts.md)

## Deterministic helper scripts

Use these scripts when applicable instead of manually inventing equivalent checks:

- `scripts/stage11_preflight.py`: inventory release-relevant repository state and verify obvious Stage 10/preflight conditions.
- `scripts/release_manifest.py`: generate an evidence-bearing release manifest with commit identity and artifact hashes.
- `scripts/smoke_http.py`: run configurable HTTP health/readiness/smoke checks without logging secret header values.
- `scripts/validate_evidence.py`: validate the Stage 11 evidence ledger and required gate coverage before PASS.
- `scripts/self_test.py`: regression-test the bundled helper scripts when the skill itself is being maintained.

Treat helper output as evidence, not as a substitute for engineering judgment. A helper `WARN` can still represent a release blocker after project-specific analysis.

# Execution protocol

## Phase 0 - Establish a release baseline

1. Locate the project root and identify repository state, languages, frameworks, package managers, lockfiles, build tools, services, databases, migrations, workers, queues, caches, storage, scheduled jobs, CI files, container files, infrastructure manifests, environment contracts, and prior deployment documentation.
2. Run the preflight helper when executable tools are available.
3. Capture the exact source identity: Git commit when available, branch/ref when relevant, dirty-tree state, version/release identifier, and build environment.
4. Locate Stage 10 evidence and verify that release-blocking security, test, or acceptance issues are not open.
5. Create or update the Stage 11 evidence ledger immediately; do not wait until the end and reconstruct evidence from memory.
6. Record assumptions and applicability decisions. Do not mark a control `N/A` merely because it is inconvenient.

Gate: `G00_PRECONDITIONS` and `G01_RELEASE_BASELINE` must be satisfied before release implementation proceeds.

## Phase 1 - Determine the target operating model

1. Derive the intended target from existing project decisions: VM/bare-metal, Docker host, orchestrator, PaaS, serverless, static hosting/CDN, desktop/mobile distribution, or hybrid.
2. Identify environments and promotion path: local, test, staging/pre-production, production, and any preview environments actually used.
3. Identify ownership boundaries for TLS, reverse proxy/ingress, DNS, secrets, database, object storage, queue, cache, monitoring, backups, and deploy credentials.
4. If a real provider is not selected or authorized, implement provider-neutral release packaging and production-like validation. Do not invent a cloud account.
5. Record runtime topology, service dependencies, exposed ports, trust boundaries, persistence, and expected scaling model.

## Phase 2 - Make builds reproducible and releasable

1. Require the ecosystem's dependency lock mechanism where supported; reconcile stale or conflicting lockfiles.
2. Ensure the documented production build starts from a clean checkout plus declared inputs. Eliminate hidden local-machine prerequisites where practical.
3. Separate development/test dependencies from runtime needs where the ecosystem supports it.
4. Remove reliance on development servers, hot reloaders, interactive prompts, local absolute paths, and workstation-only binaries from production execution.
5. Make build-time and runtime configuration boundaries explicit. Never bake runtime secrets into browser bundles or images.
6. Run clean install/build/test commands appropriate to the project. Repair failures instead of only describing them.
7. Record exact commands and results in Stage 11 evidence.

Gate: `G02_DETERMINISTIC_BUILD`.

## Phase 3 - Harden runtime packaging

1. Use containers for long-running server workloads when consistent with the project/target; otherwise implement the equivalent target-native packaging.
2. For containers, prefer multi-stage builds, minimal maintained base images, non-root runtime users, explicit workdirs, explicit exposed/listening ports, deterministic copy/install steps, graceful shutdown, and a narrow runtime filesystem footprint.
3. Add `.dockerignore` or equivalent packaging exclusions. Exclude VCS metadata, local secrets, caches, test output, editor files, large irrelevant assets, and build detritus.
4. Avoid privileged mode, host networking, broad host mounts, Docker socket mounts, unnecessary Linux capabilities, and writable filesystem access unless justified.
5. Ensure persistent data is external to disposable application instances.
6. Define CPU/memory/process assumptions where the target supports them. Avoid unbounded worker/thread concurrency.
7. Validate image/application startup and shutdown behavior.

Gate: `G03_RUNTIME_PACKAGING`.

## Phase 4 - Enforce configuration and secret contracts

1. Inventory every runtime configuration key and classify it as required, optional, secret, environment-specific, public client configuration, or generated value.
2. Add startup validation for required values with safe, actionable errors. Fail closed on missing critical security settings.
3. Maintain `.env.example` or equivalent with safe placeholders only. Never copy live secrets into examples, docs, manifests, build args, image layers, client bundles, logs, or evidence.
4. Define the production secret source and rotation/revocation expectations. Keep deploy credentials separate from application runtime credentials.
5. Detect environment-dependent insecure defaults such as debug mode, wildcard CORS, test credentials, permissive cookies, disabled TLS verification, default signing keys, or development database URLs.
6. Ensure client-exposed configuration contains only values safe for public disclosure.

Gate: `G04_CONFIG_AND_SECRETS`.

## Phase 5 - Make data changes deploy-safe

1. Inspect migrations and data/bootstrap jobs against the current release delta.
2. Prefer backward-compatible expand-contract rollout for schema changes used by rolling or zero-downtime releases.
3. Separate schema migration from long-running data backfill when appropriate.
4. Define who/what executes migrations, concurrency/locking behavior, retry semantics, timeout expectations, and failure handling.
5. Require backup/snapshot or another recovery control before destructive/high-risk data changes.
6. Avoid assuming down-migrations are safe. Prefer roll-forward when schema/data loss risk makes rollback unsafe.
7. Validate queue/job/cache/object-storage compatibility across the rollout window.
8. Prevent duplicate scheduled jobs or workers where deployment topology can create multiple schedulers.

Read [references/database-rollout.md](references/database-rollout.md) for the detailed decision matrix.

Gate: `G05_DATABASE_AND_DATA`.

## Phase 6 - Harden edge, network, TLS, and service boundaries

1. Define the public entrypoint and TLS termination boundary. Require HTTPS for production public traffic unless an explicitly isolated/internal architecture says otherwise.
2. Configure trusted proxy behavior intentionally; do not trust arbitrary forwarded headers.
3. Define request/body/upload limits, connection/header/request timeouts, keepalive behavior, compression, WebSocket/SSE handling, and buffering when relevant.
4. Restrict CORS to required origins/methods/headers. Avoid credentialed wildcard configurations.
5. Keep databases, caches, internal queues, admin ports, debug ports, and metrics endpoints non-public unless the architecture explicitly requires protected exposure.
6. Define egress requirements for external APIs, mail/SMS, storage, payment, identity, and webhooks when network policy matters.
7. Define DNS and certificate assumptions, but never mutate DNS or purchase resources without authorization.

Gate: `G06_EDGE_AND_NETWORK`.

## Phase 7 - Build a release pipeline with promotion discipline

1. Make CI start from the declared dependency lock and run required lint/type/test/build/security checks before release packaging.
2. Build the release artifact once when feasible; promote the same immutable artifact/image digest across environments rather than rebuilding production from a different source state.
3. Separate build/test identity from deploy identity and apply least privilege to deploy credentials.
4. Protect production deployment with the project's required approval/change-control rule. Credential possession alone is not authorization.
5. Prevent deployment from failed or untrusted branches/refs. Constrain tag/version semantics and production environment rules.
6. Make concurrency/idempotency behavior explicit so overlapping deploys cannot corrupt state.
7. Capture artifact identifiers/digests and pipeline evidence in the release manifest.

Gate: `G07_CI_CD_AND_PROMOTION`.

## Phase 8 - Apply release security and supply-chain controls

1. Run repository secret scanning using available trustworthy tooling; inspect and rotate any confirmed exposed secret instead of merely deleting it from the current file.
2. Run dependency vulnerability/audit tooling appropriate to each ecosystem and classify findings by exploitability, reachability, severity, and available fixes.
3. Scan production images/packages when supported.
4. Generate an SBOM when supported by the delivery toolchain or target requirements.
5. Pin external CI actions/plugins/build images to sufficiently immutable versions where practical.
6. Record artifact checksums/digests. Add signing/provenance when supported or required by the environment.
7. Review base images and runtime dependencies for maintenance status and unnecessary attack surface.
8. Do not waive critical/high findings silently. Document every accepted risk with owner/rationale/expiry when an actual organizational risk process exists.

Read [references/security-release.md](references/security-release.md).

Gate: `G08_SUPPLY_CHAIN_SECURITY`.

## Phase 9 - Make the service observable

1. Implement structured application logs suitable for production aggregation. Include useful request/job correlation identifiers where applicable.
2. Redact secrets, tokens, credentials, authorization headers, session values, and unnecessary personal data.
3. Implement startup/liveness/readiness semantics appropriate to the runtime. Do not make liveness depend on every downstream dependency if that would cause restart storms.
4. Provide metrics for traffic, errors, latency, saturation, resource health, queue/backlog behavior, job failures, and domain-critical operations where relevant.
5. Add distributed tracing when the system is distributed enough for traces to materially improve diagnosis.
6. Define SLI/SLO or at minimum explicit operational thresholds for critical paths, then map alerts to user-impacting symptoms and actionable infrastructure/resource conditions.
7. Define alert ownership/escalation and where operators should look first.
8. Validate that observability itself does not expose sensitive data or unauthenticated internal diagnostics.

Gate: `G09_OBSERVABILITY`.

## Phase 10 - Make recovery real

1. Inventory persistent state and assign backup responsibility for each store.
2. Define RPO, RTO, retention, encryption, isolation, access control, lifecycle, and restore prerequisites appropriate to project decisions.
3. Verify backups are restorable. Prefer an actual non-production restore drill when the environment permits it.
4. Define rollback and roll-forward separately for application artifact, schema, configuration, infrastructure, and data.
5. Define incident-safe steps for failed deploy, partial deploy, unhealthy instance, migration failure, secret compromise, external dependency outage, and data-recovery event where applicable.
6. Keep rollback instructions version-aware and evidence-backed. Do not promise rollback if the migration/data change makes it unsafe.

Read [references/recovery-release-strategy.md](references/recovery-release-strategy.md).

Gate: `G10_BACKUP_RESTORE` and `G11_RELEASE_STRATEGY`.

## Phase 11 - Execute production-like validation

1. Build the exact release artifact/image from the intended source identity.
2. Start it using production-equivalent runtime settings with safe test/staging secrets.
3. Validate startup, liveness/readiness, critical public routes, authentication boundary behavior, database connectivity/migrations, queues/workers/jobs, object storage, cache behavior, static assets, and external integration stubs/sandboxes as applicable.
4. Validate graceful shutdown/restart and ensure in-flight jobs/requests follow the application's durability model.
5. Run the project's Stage 10 regression suite as needed after deployment-related changes; deployment fixes must not silently break application behavior.
6. Use `scripts/smoke_http.py` for repeatable HTTP smoke checks when applicable.
7. Repair defects and repeat the affected checks until clean.

Gate: `G12_PRODUCTION_LIKE_VALIDATION`.

## Phase 12 - Perform real deployment only when authorized

1. Require an explicit target, explicit authorization for the mutating action, and valid scoped credentials/access before creating resources, changing DNS, applying production migrations, or exposing the service publicly.
2. Follow the approved deployment strategy: rolling, blue-green, canary, recreate, or target-native equivalent. Record why it fits this system.
3. Execute pre-deploy backup/snapshot and migration prerequisites when required.
4. Deploy the immutable release candidate and record target-side evidence such as deployment/revision ID, image digest, timestamp, health state, and release URL only when actually observable.
5. Execute post-deploy smoke/health validation and observe the defined early-release signals.
6. Trigger rollback/roll-forward when release criteria fail; do not keep a broken release live merely to finish the stage.
7. If the real target is unavailable or unauthorized, set external deployment to `NOT_PERFORMED` and continue all production-like work that does not require that dependency.

Gate: `G13_DEPLOYMENT_TRUTH` validates truthfulness and safety; a real external deployment is not mandatory for PASS unless the higher-level project explicitly defines it as mandatory.

## Phase 13 - Assemble evidence and hand off

Create/update all applicable artifacts:

- production runtime/container configuration;
- target orchestration/deployment manifests where applicable;
- CI/CD workflow(s);
- `.env.example` or equivalent configuration contract;
- `docs/11-deployment.md`;
- `docs/11-operations-runbook.md`;
- `docs/11-release-report.md`;
- `artifacts/stage-11/release-manifest.json`;
- `artifacts/stage-11/evidence.json`;
- `project-state.json`.

Generate the release manifest with `scripts/release_manifest.py` when possible. Validate the evidence ledger with `scripts/validate_evidence.py` before PASS.

Record at minimum: source identity, build commands/results, artifact identities/hashes, target model, environment/config model, migration plan/result, health checks, security scans, observability, backup/restore evidence, rollout strategy, smoke results, real-deployment truth status, residual risks, and Stage 12 handoff.

Gate: `G14_EVIDENCE_AND_HANDOFF`.

# Mandatory remediation loop

For every failing applicable gate:

1. Diagnose the root cause from real evidence.
2. Classify the defect: repository/build, configuration, runtime/container, data/migration, edge/network, pipeline, supply chain, observability, recovery, or external blocker.
3. Implement the smallest production-grade correction consistent with prior architecture.
4. Run targeted validation for the changed subsystem.
5. Re-run dependent gates that could have regressed.
6. Update evidence with actual commands/results/artifact identifiers.
7. Continue until PASS, true BLOCKED, or justified FAIL.

Do not convert a technical defect into `BLOCKED` just because repair is inconvenient.

# Stage boundary and safety

Do not:

- create paid cloud resources, purchase domains/certificates, change public DNS, or expose services publicly without explicit authorization;
- use real customer data for smoke testing unless explicitly authorized and necessary safeguards exist;
- print or commit credentials;
- disable security scanners, tests, certificate validation, authorization, or data protections to force a green pipeline;
- run irreversible/destructive database operations without verified prerequisites and authorization;
- silently rewrite architecture outside Stage 11 scope;
- claim high availability, zero downtime, disaster recovery, compliance, or successful deployment without evidence supporting the claim.

# Completion decision

Before emitting a completion marker:

1. Read [references/quality-gates.md](references/quality-gates.md).
2. Validate every applicable mandatory gate.
3. Ensure no unresolved P0/P1 release blocker remains.
4. Ensure evidence references are real and reproducible.
5. Ensure Stage 12 receives a precise release-candidate handoff rather than a generic summary.
6. Update `project-state.json` without deleting unknown fields.

On success, end with exactly:
`STAGE_11_STATUS: PASS`
`NEXT_STAGE: 12-fullstack-final-review`

On a true external blocker, end with exactly:
`STAGE_11_STATUS: BLOCKED`
`NEXT_STAGE: NONE`

On an unresolved technical/release failure, end with exactly:
`STAGE_11_STATUS: FAIL`
`NEXT_STAGE: NONE`
