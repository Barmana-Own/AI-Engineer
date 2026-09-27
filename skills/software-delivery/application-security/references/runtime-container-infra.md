# Runtime, Container, Reverse Proxy, and Deployment Security Review

## Table of contents

1. Production/runtime modes
2. Configuration separation
3. Process privilege
4. Container hardening
5. Network exposure and ports
6. Reverse proxy/trusted proxy
7. Security headers/TLS boundary
8. Health/debug/metrics surfaces
9. Databases/caches/queues/storage
10. Resource limits and timeouts
11. Deployment secrets
12. Tests and evidence

## 1. Production/runtime modes

Verify production artifacts do not enable development/debug behavior such as verbose stack traces, hot reload/dev servers, insecure test routes, interactive debuggers or debug authentication bypasses.

Check actual entrypoints and deployment commands rather than relying only on environment variable names.

## 2. Configuration separation

Review configuration defaults. Production should fail safely when required security configuration is missing rather than silently using weak development defaults.

Be cautious with defaults for:

- JWT/session secrets;
- admin credentials;
- database passwords;
- CORS origins;
- debug mode;
- cookie `Secure` behavior;
- trusted proxies;
- public storage;
- webhook verification.

A hardcoded fallback secret is a finding even if documentation says operators should override it.

## 3. Process privilege

Run application processes with least practical OS/container privilege. Review:

- root execution;
- writable directories;
- filesystem access;
- privileged ports;
- host mounts;
- device access;
- Docker socket exposure;
- service-account/cloud permissions represented in configuration.

Do not break required functionality solely to force a generic hardening rule; document necessary privileges and reduce them where practical.

## 4. Container hardening

For Docker/compatible configurations, inspect:

- minimal/reasonable base image;
- multi-stage build to avoid build secrets/tools in runtime image;
- non-root `USER` where feasible;
- secrets not copied into image layers;
- `.dockerignore` coverage;
- no Docker socket unless explicitly required;
- capabilities/privileged mode;
- read-only filesystem where compatible;
- writable temp/data volumes intentionally scoped;
- exposed ports vs published ports;
- healthcheck behavior;
- package/cache cleanup only as maintainability requires.

Do not bake `.env`, SSH keys, npm tokens or cloud credentials into images.

## 5. Network exposure and ports

Review compose/orchestration/reverse-proxy definitions for databases, Redis, RabbitMQ management, MinIO console, metrics/debug ports and admin UIs accidentally published to all interfaces.

Internal services should not be internet-exposed without a documented requirement and authentication/network controls.

## 6. Reverse proxy and trusted proxy

For frameworks that derive client IP, scheme or secure-cookie behavior from proxy headers, configure trusted proxy semantics precisely. Blindly trusting all `X-Forwarded-*` headers can enable IP/scheme/host spoofing when the app is directly reachable.

Review Host header use in password-reset links, redirects and absolute URLs. Prefer configured canonical origins for security-sensitive links.

## 7. Security headers and TLS boundary

Identify whether headers/TLS are set at app, proxy, CDN or load balancer. Avoid duplicate conflicting policies.

HSTS belongs on HTTPS production origins and must account for domain/subdomain deployment policy. Do not enable preload-style behavior casually.

CSP should reflect actual application assets and be tested rather than set to a generic value that breaks the product.

## 8. Health, debug, and metrics surfaces

Health endpoints should expose only necessary status, not full environment, secrets, dependency credentials or stack traces. Metrics/admin dashboards should have appropriate network/auth controls.

Search for framework debug endpoints, test routers, API docs consoles and development admin panels. Determine intended production exposure.

## 9. Databases, caches, queues, and storage

Review service configuration represented in repo:

- authentication enabled where exposure requires it;
- non-default credentials in production through secret injection;
- network binding/publication;
- TLS where required by environment/threat model;
- least-privilege accounts/vhosts/buckets;
- persistence/backups if security availability/integrity requires it;
- management interfaces not unnecessarily exposed.

Application-level controls remain necessary even when services are on a private network.

## 10. Resource limits and timeouts

Review:

- HTTP body/upload size;
- request timeouts;
- outbound connection/read timeouts;
- worker concurrency;
- queue retry/backoff/dead-letter behavior;
- database connection pool limits;
- container CPU/memory limits if deployment artifacts manage them;
- log growth/rotation assumptions where visible.

This is defensive resource governance, not a requirement to perform load testing.

## 11. Deployment secrets

Inspect build/deploy files for secret leakage through:

- Docker `ARG`/`ENV` layers;
- CI command output;
- generated static files;
- compose files committed with credentials;
- startup command arguments visible in process lists;
- mounted secret files with overly broad permissions.

Use deployment-specific secret stores/environment injection without embedding real values in the repository.

## 12. Tests and evidence

Useful evidence includes:

- container build succeeds after hardening;
- runtime starts as intended;
- production config rejects missing mandatory secret;
- internal service port is no longer published externally in compose;
- debug route is disabled in production mode;
- trusted proxy behavior has a targeted config/test assertion;
- health endpoint omits sensitive detail.
