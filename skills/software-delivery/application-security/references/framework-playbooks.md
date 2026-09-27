# Stack-Specific Security Playbooks

## Table of contents

1. How to use this file
2. Node.js general
3. Express
4. Next.js
5. React/Vite/browser SPA
6. MySQL and SQL access
7. Redis
8. RabbitMQ
9. S3/MinIO object storage
10. Docker/Compose
11. Nginx/reverse proxy/API gateway
12. OAuth/OIDC/JWT libraries
13. GraphQL
14. WebSockets
15. Python services
16. PHP/Laravel and other detected stacks

## 1. How to use this file

Apply only sections matching technologies actually detected in the repository. This is a focused prompt list, not a substitute for reading the project's framework documentation. When current framework behavior matters, consult authoritative current documentation.

Do not report a finding simply because a framework supports an unsafe feature. Verify that the project enables/uses it unsafely.

## 2. Node.js general

Review:

- supported runtime version and package-manager lockfile;
- `child_process`/shell execution with untrusted data;
- filesystem path construction;
- dynamic `eval`/`Function`/VM use;
- prototype/object merge behavior for client-supplied nested objects;
- unsafe deserialization libraries;
- HTTP client redirects/timeouts/response limits;
- TLS verification overrides;
- environment variables exposed to frontend/build output;
- unhandled promise rejection/error paths affecting security checks;
- temporary file handling;
- regexes on attacker-controlled large input when catastrophic backtracking is plausible.

Prefer library APIs over shell commands. Do not disable TLS verification globally.

## 3. Express

Review middleware order as a security control. Authentication/authorization/validation can fail if mounted after sensitive routers.

Check:

- route inventory and duplicate/legacy routers;
- `express.json`/body-parser size limits;
- upload limits;
- schema validation before domain operations;
- centralized error handler and production stack-trace behavior;
- Helmet/header strategy if used;
- CORS exact-origin configuration;
- CSRF according to cookie/bearer architecture;
- `trust proxy` correctness;
- secure cookie flags;
- session store, TTL, fixation/regeneration semantics;
- rate limiting on auth/expensive endpoints;
- route-level object/tenant authorization;
- static file roots and user-upload exposure;
- raw body preservation for webhook signatures when required.

Do not make `app.use(cors())` with broad defaults a substitute for API authorization.

## 4. Next.js

Determine whether the project uses App Router, Pages Router, Route Handlers, Server Actions, middleware, Edge runtime or a mixture.

Review:

- Route Handlers/API routes for server-side authorization;
- Server Actions as externally invokable server entry points that require their own authorization/validation;
- middleware as routing/early enforcement but not the sole authorization layer for sensitive domain actions;
- server/client component boundaries;
- accidental import/exposure of server-only secrets into client bundles;
- `NEXT_PUBLIC_*` variables as public;
- `dangerouslySetInnerHTML` and rich-content rendering;
- redirects/return URLs;
- cache/revalidation behavior for user/tenant-specific data;
- static generation/ISR accidentally caching private content;
- image/remote URL configuration when user-controlled remote resources are involved;
- file upload route/body limits;
- production error/debug source exposure;
- authentication library session callbacks/claims and authorization freshness;
- server action argument trust;
- route groups/rewrites/proxy rules that expose alternate paths.

For cached server data, ensure cache keys/scope cannot mix users or tenants and that private responses are not made public by framework caching semantics.

## 5. React, Vite, and browser SPAs

Treat the browser as untrusted. Review:

- client-side role/route guards as UX only;
- storage of bearer/refresh tokens and XSS implications;
- `dangerouslySetInnerHTML`, DOM `innerHTML`, URL rendering and rich text;
- environment variables embedded by the build system;
- source-map/public config leakage;
- open redirects in router return paths;
- postMessage origin validation if used;
- iframe/sandbox handling;
- file preview/object URL lifecycle;
- third-party scripts and integrity/trust implications;
- API base URL selection and accidental dev/admin endpoints.

Do not place secrets in Vite `VITE_*` variables or equivalent public build variables.

## 6. MySQL and SQL access

Review the actual database library/ORM/raw-query paths.

Check:

- parameterized values;
- allowlisted dynamic identifiers/order fields;
- raw SQL escape hatches;
- tenant/ownership predicate consistency;
- transaction boundaries for financial/state operations;
- unique constraints enforcing one-time invariants;
- decimal/money precision;
- database account least privilege represented in config;
- migration/admin credential separation where feasible;
- SQL error leakage;
- connection TLS requirements according to deployment;
- backups/dumps excluded from public/source artifacts.

For ORMs, verify generated queries and authorization semantics rather than assuming ORM usage eliminates injection or tenant flaws.

## 7. Redis

Identify whether Redis stores cache, sessions, queues, rate limits or authorization-sensitive state.

Review:

- network exposure/public port;
- authentication/TLS according to environment;
- logical key namespace including tenant/user where required;
- session TTL/revocation;
- cache keys that could mix tenants/users;
- serialization of untrusted objects;
- Lua scripts/dynamic command construction;
- rate-limit atomicity;
- sensitive data retention;
- eviction implications for security controls such as rate limits/session state.

A cache miss must not weaken authorization.

## 8. RabbitMQ

Review:

- management UI exposure;
- credentials/vhost/permissions;
- TLS/network boundary as required;
- queue message schema validation;
- tenant/user context propagation;
- publisher ability to invoke privileged consumers;
- duplicate delivery/idempotency;
- retry/backoff/dead-letter handling;
- poison-message behavior;
- sensitive data in message bodies/logs;
- consumer concurrency and state races.

Treat message authenticity/authorization according to who can publish to the queue, not merely because traffic is "internal."

## 9. S3/MinIO object storage

Review:

- bucket default privacy;
- bucket policies/ACLs represented in repo;
- admin/access keys and frontend exposure;
- server-generated object keys;
- object ownership/tenant mapping in application database;
- presigned URL action (GET/PUT), object key, content constraints and TTL;
- stale signed URLs after authorization/state change;
- upload content/size validation;
- derived thumbnail/preview privacy;
- public website/static bucket vs private data bucket separation;
- console/API port exposure for MinIO;
- lifecycle/cleanup for temporary/orphaned objects.

Do not use bucket obscurity as authorization.

## 10. Docker and Compose

Review Dockerfile/compose for:

- production image uses production entrypoint, not dev server;
- non-root user where feasible;
- no secrets in build args/layers/copied `.env`;
- `.dockerignore` prevents unnecessary secret/source artifacts from build context;
- privileged mode/capabilities/devices;
- Docker socket mounts;
- host filesystem mounts;
- internal services not broadly published;
- image tags/versioning;
- health checks without secret leakage;
- writable filesystem needs;
- environment defaults not using weak credentials.

Build and run smoke tests after hardening when feasible.

## 11. Nginx, reverse proxies, and API gateways

Review:

- TLS termination assumptions;
- forwarded host/proto/client IP trust;
- header overwrite vs pass-through;
- body/upload size limits;
- path normalization and proxy path rewriting;
- accidental exposure of internal routes;
- static/upload aliases;
- auth_request or gateway policy consistency;
- caching of authenticated/private responses;
- security headers ownership;
- websocket upgrade rules;
- error pages hiding upstream internals;
- admin/metrics endpoints.

Ensure the app cannot be reached through an alternate path that bypasses gateway-only controls if the architecture relies on them.

## 12. OAuth/OIDC and JWT libraries

Follow the specific library's current documentation. Review:

- signature verification and allowed algorithms;
- issuer/audience/token type;
- key/JWKS source and caching;
- `kid`/key selection safety;
- expiry/not-before handling;
- state/nonce/PKCE for browser authorization flows;
- refresh-token storage/rotation;
- account linking;
- session/logout semantics;
- stale role/permission claims.

Never implement JWT signature verification manually when a maintained library is available.

## 13. GraphQL

If present, review:

- resolver-level authorization, not only top-level query authentication;
- object/field authorization;
- introspection policy according to product requirements;
- query depth/complexity/resource limits;
- batching/alias abuse;
- pagination limits;
- error detail leakage;
- file upload handling;
- subscriptions/WebSocket authentication lifecycle;
- DataLoader/cache keys and tenant isolation.

A schema type hiding a field in the UI does not enforce authorization unless resolver access is controlled.

## 14. WebSockets

Review:

- authentication at connection and/or message boundary;
- session/token expiry after long-lived connection;
- origin validation where relevant to browser cookie authentication;
- channel/room authorization;
- tenant isolation;
- message schema/size/rate limits;
- reconnect/replay semantics;
- server broadcasts not leaking across rooms/tenants;
- privileged event names not client-invokable without policy checks.

## 15. Python services

When Python is detected, review relevant framework patterns:

- `subprocess(..., shell=True)` and command construction;
- unsafe pickle/YAML loading;
- Flask/Django/FastAPI debug/development configuration;
- template autoescape bypasses;
- ORM raw SQL;
- Pydantic/schema validation boundaries;
- Django CSRF/session/cookie settings if applicable;
- file path and upload handling;
- SSRF via `requests`/httpx redirects/timeouts;
- secrets in settings modules.

Apply framework-specific current documentation rather than generic assumptions.

## 16. PHP/Laravel and other detected stacks

When a stack is not covered in detail here:

1. identify framework version and security architecture;
2. consult authoritative current framework security documentation when needed;
3. map the mandatory Stage 08 domains to framework-native controls;
4. inspect escape hatches/raw APIs;
5. add tests using the project's native test framework;
6. keep the same evidence/severity/gate rules.

For Laravel/PHP specifically, inspect authorization policies/gates, request validation, CSRF/web middleware, mass assignment/fillable/guarded behavior, Blade escaping/raw output, query builder/raw SQL, signed URLs/storage privacy, debug mode and session/cookie configuration.
