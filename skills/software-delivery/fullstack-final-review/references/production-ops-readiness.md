# Production and Operations Readiness

## Contents

- Configuration
- Build and process model
- Containers
- Health and readiness
- Deployment and migration order
- Rollback
- Observability
- Backups and state
- Operational blockers

Evaluate readiness for the deployment model the project actually claims to support.

## Configuration

Verify:
- required environment variables are documented;
- `.env.example`/templates contain placeholders, not live secrets;
- production mode does not fall back to dev/mock services silently;
- secret values are injected externally;
- secure defaults exist where possible;
- environment-specific URLs/origins are configurable;
- debug verbosity is disabled in production by default.

## Build and process model

Verify:
- production build command works;
- production start/entrypoint exists and references built artifacts correctly;
- working directories/paths are correct in containers/services;
- process exits non-zero on fatal startup configuration errors;
- workers/schedulers required by core flows are included in deployment topology;
- graceful shutdown is reasonable for requests/jobs/DB connections.

## Containers

When containers are part of delivery, inspect:
- Dockerfile stages and copy paths;
- dependency installation reproducibility;
- runtime user/permissions where practical;
- exposed ports and health checks;
- secret handling (not baked into image);
- `.dockerignore` hygiene;
- startup command;
- multi-service dependency/readiness assumptions.

Build/start representative production images when technically possible.

## Health and readiness

A liveness endpoint should prove process viability; readiness should reflect critical dependency readiness where architecture requires it.

Check that health endpoints:
- do not expose secrets/internal dumps;
- have appropriate access if they reveal operational detail;
- return failing status when the service cannot safely receive traffic;
- are compatible with the intended orchestrator/load balancer.

## Deployment and migration order

Document the safe order for:
- config/secrets;
- database migrations;
- app rollout;
- workers;
- cache/job compatibility;
- traffic cutover;
- post-deploy smoke.

For potentially incompatible schema changes, document compatibility/rollback limits.

## Rollback

A credible rollback plan should state:
- application rollback method;
- DB migration reversibility or forward-fix strategy;
- what data changes cannot be rolled back;
- backup/restore dependency when applicable;
- how to verify recovery.

Do not claim rollback is safe when a destructive migration makes it impossible.

## Observability

Proportional to system risk, verify:
- structured/useful logs;
- correlation/request identifiers when architecture benefits;
- error visibility;
- key service health metrics;
- queue/worker failure visibility;
- alerting/runbook expectations where provided;
- secrets/private payloads are not intentionally logged.

Missing advanced observability is not always release-blocking, but inability to detect failure of a core asynchronous workflow can be.

## Backups and state

For stateful production systems, documentation should identify:
- backup responsibility/mechanism;
- restore expectations;
- persistent volumes/object storage;
- critical data retention assumptions.

Final review does not perform destructive restore tests on production. Use isolated verification if available.

## Operational blockers

Examples:
- no valid production start command;
- image/build starts in dev server mode when production mode is required;
- core worker omitted from deployment;
- migration order undocumented and unsafe;
- secrets baked into image/repo;
- health always returns OK despite fatal dependency failure where readiness matters;
- no viable recovery/forward-fix story for a migration known to be destructive.
