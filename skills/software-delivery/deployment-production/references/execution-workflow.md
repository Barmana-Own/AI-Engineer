# Stage 11 Execution Workflow

## Table of contents

1. Operating principles
2. Phase A - Repository discovery
3. Phase B - Release delta and risk map
4. Phase C - Build reproducibility
5. Phase D - Runtime packaging
6. Phase E - Environment and secrets
7. Phase F - Data and stateful dependencies
8. Phase G - Edge and network behavior
9. Phase H - CI/CD and artifact promotion
10. Phase I - Security and supply chain
11. Phase J - Observability and operational controls
12. Phase K - Backup and recovery
13. Phase L - Production-like execution
14. Phase M - Real deployment
15. Phase N - Post-deploy verification
16. Phase O - Evidence and handoff
17. Remediation sequencing
18. Stop conditions

## 1. Operating principles

Execute Stage 11 as engineering work, not as a documentation exercise. Inspect before editing, edit before declaring, test after editing, and preserve evidence after testing.

Use the following priority order when multiple problems exist:

1. P0 safety/security/data-loss risks.
2. Stage precondition failures.
3. Build and startup blockers.
4. Migration/data compatibility risks.
5. Secret/configuration defects.
6. Release pipeline/integrity defects.
7. Network/TLS/runtime hardening.
8. Observability and recovery gaps.
9. Documentation and handoff completeness.

Avoid large unrelated refactors. Stage 11 may change application code when production readiness requires it, for example to add graceful shutdown, health endpoints, config validation, structured logging, or idempotent worker behavior.

## 2. Phase A - Repository discovery

Before changing files:

- Identify the repository root and version-control state.
- Enumerate top-level services/apps/packages.
- Identify languages and runtime versions from authoritative project files.
- Identify dependency manifests and lockfiles.
- Identify build/test/lint/type-check scripts.
- Identify server entrypoints and process managers.
- Identify frontend static build outputs and runtime/public configuration.
- Identify database engines, migrations, seeders, ORM tools, schema files, and connection pools.
- Identify queues, workers, scheduled jobs, cache, search, object storage, email/SMS, payment, identity, webhooks, and other external dependencies.
- Identify Dockerfiles, Compose files, Kubernetes/Helm manifests, Procfiles, serverless files, systemd units, reverse-proxy configs, and IaC.
- Identify CI/CD providers and environment/protection configuration represented in source.
- Identify existing health endpoints, metrics, logging, error reporting, tracing, backup scripts, and runbooks.
- Identify `.env*`, config templates, secrets references, and secret-manager integration.
- Inspect `project-state.json` and Stage 10 outputs.

Run `scripts/stage11_preflight.py --root <project-root> --json-out artifacts/stage-11/preflight.json` when possible.

Do not treat tool detection as proof that the implementation is correct. Open the relevant files and inspect behavior.

## 3. Phase B - Release delta and risk map

Build a short release-risk map before implementation. Record:

- source commit/ref;
- intended release/version identifier;
- changed services/components since the previous known release when identifiable;
- schema/data changes;
- new/changed secrets or config keys;
- changed public routes/domains/ports;
- changed dependencies or base images;
- new background jobs/schedulers;
- new external integrations;
- changes that alter persistence or data format;
- changes requiring coordinated deploy order;
- features guarded by flags;
- known residual Stage 10 warnings.

Assign each risk an owner/control and verification action. Do not create a generic risk list detached from the release delta.

## 4. Phase C - Build reproducibility

For each deployable unit:

1. Determine the supported runtime/toolchain version from repository configuration.
2. Check for a lockfile or equivalent reproducibility mechanism.
3. Detect multiple conflicting package-manager lockfiles and resolve intentionally.
4. Confirm clean dependency installation using frozen/immutable lock mode where supported.
5. Run code generation before build if the repository requires it.
6. Run lint/type/test steps required by the project's release policy.
7. Run the production build.
8. Verify expected build output exists and is not empty/stale.
9. Verify production startup does not invoke a development server.
10. Record exact command, exit code, duration when available, and relevant output summary.

If a build depends on environment values, classify those values as build-time public config versus runtime secret/config. Never inject a server secret into a client build.

For monorepos, validate dependency graph/order and build each actual deployable target. Do not assume root build success validates every service.

## 5. Phase D - Runtime packaging

For server workloads using containers, inspect or implement:

- maintained base image compatible with the runtime;
- explicit runtime version rather than floating major-unknown tags where reproducibility matters;
- multi-stage build when it reduces runtime dependencies/toolchains;
- deterministic dependency install;
- non-root user where feasible;
- correct ownership/permissions on runtime files;
- no package-manager cache/build cache in final image unless required;
- no source-only credentials, `.env`, SSH keys, cloud credentials, Git metadata, or local test fixtures in final image;
- explicit runtime command/entrypoint;
- signal propagation and graceful shutdown;
- runtime port and bind address compatible with target;
- health behavior compatible with target probes;
- writable paths known and minimized;
- persistent data externalized;
- image labels/version metadata when useful.

For PaaS/serverless/static deployments, apply equivalent checks to the target-native artifact and runtime model instead of forcing Docker.

Validate packaging by building and starting the artifact locally or in a production-like environment when possible.

## 6. Phase E - Environment and secrets

Create an environment matrix containing at least:

- key name;
- required/optional;
- secret/non-secret;
- build-time/runtime;
- server/client exposure;
- default allowed in production?;
- validation rule;
- source/owner;
- rotation/restart impact.

Check for:

- missing required values;
- fallback signing/encryption keys;
- debug flags;
- development URLs;
- default admin credentials;
- wildcard CORS with credentials;
- insecure cookie/session flags;
- disabled TLS verification;
- insecure webhook validation;
- production storage pointing to local ephemeral disk unexpectedly;
- secret values in documentation, code, CI files, images, or examples.

Startup errors may name a missing variable but must not print its secret value.

## 7. Phase F - Data and stateful dependencies

Build a dependency inventory for all persistent/stateful systems:

- primary database;
- replicas;
- cache;
- queue/broker;
- object/blob storage;
- search/index;
- vector database if used;
- files/volumes;
- scheduler state;
- third-party durable state.

For each, record connectivity, authentication, encryption, persistence, backup responsibility, migration/versioning, readiness behavior, and failure impact.

Use the detailed migration rules in `database-rollout.md` before approving schema changes.

## 8. Phase G - Edge and network behavior

Verify the complete request path from public client to application:

- DNS ownership assumption;
- CDN/WAF if any;
- TLS termination;
- reverse proxy/ingress/load balancer;
- forwarded header trust;
- application bind address/port;
- route prefixes/base path;
- body/upload size limits;
- timeout budget;
- WebSocket/SSE upgrade behavior;
- compression;
- static asset caching;
- CORS;
- CSRF/cookie domain and secure flags when applicable;
- health/metrics exposure.

Test at least one request through the same proxy path used by production-like validation when possible. Direct-to-process tests alone can miss proxy/header/cookie errors.

## 9. Phase H - CI/CD and artifact promotion

A production pipeline should separate these concerns:

1. source validation;
2. dependency restore/install;
3. lint/type/test;
4. build/package;
5. security scans;
6. artifact publication;
7. environment approval if required;
8. pre-deploy checks/backup;
9. migration coordination;
10. immutable artifact deployment;
11. health/smoke verification;
12. rollback/roll-forward on failure;
13. release evidence capture.

Prefer building once and promoting by artifact digest. If the platform necessarily rebuilds, document why and ensure source/dependency identity remains fixed.

Protect production deploy credentials from untrusted pull requests/forks. Avoid shell interpolation patterns that allow attacker-controlled refs/inputs to become commands.

## 10. Phase I - Security and supply chain

Apply `security-release.md`. At minimum perform the available equivalents of:

- secret scanning;
- dependency audit;
- image/package scanning;
- SBOM generation where supported;
- action/plugin pinning review;
- artifact digest capture;
- dangerous runtime privilege review;
- public exposure review.

A scanner error is not a passing scan. Record scanner unavailable/error distinctly and determine whether another trustworthy control is required.

## 11. Phase J - Observability and operational controls

Apply `observability-operations.md`.

Verify operators can answer:

- Is the service up?
- Is it ready for traffic?
- Are users seeing errors?
- Is latency degraded?
- Is a dependency failing?
- Are queues/jobs backing up?
- Are resources saturated?
- Did the new release cause the change?
- Which request/job can be traced across services?
- Where should the operator look next?

If those questions cannot be answered for critical paths, operational readiness is incomplete.

## 12. Phase K - Backup and recovery

Apply `recovery-release-strategy.md`.

For each durable store, verify:

- backup mechanism;
- schedule/trigger;
- retention;
- encryption;
- access isolation;
- off-host/off-instance durability as appropriate;
- restore procedure;
- restore credentials/access;
- expected RPO/RTO;
- last verified restore or a planned validation when execution is unavailable.

A backup command that has never been restored should be reported as unverified, not as proven recovery.

## 13. Phase L - Production-like execution

Construct the closest safe environment available to production. Use real application artifacts and production-equivalent process topology, but use non-production credentials/data unless explicitly authorized.

Validate:

- clean startup;
- startup failures on invalid critical config;
- readiness transition;
- liveness behavior;
- basic public route;
- authentication/session boundary;
- critical write/read path where safe;
- migrations;
- worker/queue flow;
- scheduled job behavior or scheduling guard;
- object storage upload/read/delete if applicable;
- cache degradation/fallback if applicable;
- static assets;
- external integration sandbox/stub paths;
- graceful shutdown/restart;
- logs/metrics/errors during the tests.

Keep smoke tests idempotent and clean up test records where feasible.

## 14. Phase M - Real deployment

Perform only after authorization and access checks. Before mutating production:

- record approved target and scope;
- record source/artifact identity;
- verify backup/migration prerequisites;
- verify current service health baseline;
- confirm rollback/roll-forward trigger;
- confirm deploy credential scope;
- confirm no open release blocker.

During deployment, record target-side IDs/timestamps. Avoid exposing tokens/secret output in evidence.

## 15. Phase N - Post-deploy verification

After a real deployment:

- verify the deployed revision/artifact digest;
- verify health/readiness from the target perspective;
- run external smoke tests;
- inspect error rate/latency/saturation and release-specific signals;
- verify migration status;
- verify workers/jobs;
- verify critical integration callbacks where safe;
- watch for crash loops/restarts;
- compare key signals to the pre-deploy baseline when available.

If acceptance thresholds fail, follow the defined rollback/roll-forward decision. Do not normalize an unhealthy release.

## 16. Phase O - Evidence and handoff

Complete `release-manifest.json`, `evidence.json`, deployment docs, runbook, release report, and project state.

The Stage 12 handoff must tell the reviewer exactly:

- what source/artifact constitutes the release candidate;
- what was actually deployed versus only prepared;
- which gates passed and how;
- what residual risks remain;
- what warnings were accepted and why;
- what environment assumptions remain external;
- what Stage 12 should independently verify.

## 17. Remediation sequencing

After any change, rerun the smallest affected set first, then broader dependent checks. Examples:

- Dockerfile change -> rebuild image -> startup -> probes -> smoke -> image scan.
- env validation change -> unit/config test -> startup valid -> startup invalid -> smoke.
- migration change -> migration test -> app compatibility -> backup/recovery review -> smoke.
- reverse proxy change -> config validation -> proxy startup -> forwarded headers/TLS/CORS/upload tests.
- CI workflow change -> syntax/lint if available -> dry validation -> permissions/secrets review.
- logging change -> regression test -> log redaction inspection -> smoke.

## 18. Stop conditions

Stop with `BLOCKED` only for genuine external dependencies that prevent required execution.

Stop with `FAIL` when a release-blocking technical defect remains unresolved, remediation would require unsafe/destructive action outside authorization, or project integrity cannot be established.

Do not stop merely because the first build, migration, or smoke test fails. Repair and rerun.
