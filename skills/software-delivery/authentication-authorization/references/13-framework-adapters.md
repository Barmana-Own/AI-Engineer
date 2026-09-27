# Framework and Stack Adapters

## Contents

- [Purpose](#purpose)
- [Node.js / Express](#nodejs-express)
- [Next.js](#nextjs)
- [React / Vite SPA](#react-vite-spa)
- [NestJS](#nestjs)
- [Django / Django REST Framework](#django-django-rest-framework)
- [Flask](#flask)
- [Laravel](#laravel)
- [Rails](#rails)
- [Spring Boot / Spring Security](#spring-boot-spring-security)
- [ASP.NET Core](#aspnet-core)
- [Go](#go)
- [GraphQL](#graphql)
- [WebSocket/realtime frameworks](#websocketrealtime-frameworks)
- [ORMs and database access](#orms-and-database-access)
- [CI/CD](#cicd)


## Purpose

Use only the sections matching the project's actual stack. These are implementation cues, not substitutes for reading the exact installed framework/library documentation.

## Node.js / Express

### Discovery

Look for:

- `express-session`, session stores;
- `passport` strategies;
- `jsonwebtoken`, `jose`, `openid-client` or provider SDKs;
- bcrypt/argon2/scrypt wrappers;
- route middleware such as `authenticate`, `authorize`, `requireRole`, `requirePermission`;
- validation libraries;
- ORM models for users/sessions/refresh tokens/roles/memberships;
- proxy configuration via `app.set('trust proxy', ...)`;
- CORS/CSRF middleware;
- request logging that may capture auth headers/bodies.

### Express pitfalls

- Ensure middleware ordering does not place protected routes before auth middleware.
- Router-level middleware can be bypassed if an equivalent route is mounted elsewhere.
- Configure `trust proxy` only for the actual proxy topology before relying on secure-cookie or source-IP behavior.
- Do not trust `X-Forwarded-For` directly in rate limiting without trusted proxy configuration.
- Do not expose `req.user` from an unverified decoded JWT.
- Centralize error handling so token/library errors do not leak internals.
- Use explicit body-field allowlists for role/tenant/owner/security fields.

## Next.js

Determine architecture first:

- App Router vs Pages Router;
- server actions;
- route handlers/API routes;
- middleware;
- server components;
- client components;
- external backend vs same application.

### Next.js pitfalls

- Middleware/route redirects are UX/perimeter aids; protect the server action/route/data operation itself.
- Server Actions must perform authorization inside the action/service; hiding the form is insufficient.
- Do not expose secrets through `NEXT_PUBLIC_*` variables.
- Treat cookies read/written by server code according to the auth architecture and current Next.js APIs.
- Verify cache behavior for authenticated/tenant-scoped data; avoid sharing private cached output across users/tenants.
- Validate redirect destinations passed to `redirect()` or auth callbacks.
- Distinguish server-only modules from client bundles to avoid token/secret leakage.

If using an auth framework such as Auth.js or a hosted provider, inspect callbacks/hooks and database adapter behavior rather than assuming defaults solve application authorization.

## React / Vite SPA

- Treat route guards as UX only.
- Inspect where bearer tokens are stored.
- Implement one controlled refresh flow rather than ad hoc refresh in every request.
- Prevent refresh retry loops.
- Ensure error monitoring does not capture Authorization headers/tokens.
- Use server permission data for UI capability decisions.
- Validate post-login return routes.

## NestJS

Look for:

- guards;
- interceptors;
- decorators/metadata;
- Passport strategies;
- module-global guards;
- DTO validation/transform behavior;
- GraphQL guards/resolvers if used.

Pitfalls:

- a decorator without a global/route guard does not enforce anything;
- resource/tenant rules often belong in service/policy logic, not only role decorators;
- ensure guards apply to GraphQL/websocket contexts as well as HTTP if those transports exist;
- protect privileged DTO fields against mass assignment.

## Django / Django REST Framework

Look for:

- Django auth user model;
- authentication backends;
- middleware;
- DRF authentication classes;
- permission classes;
- object-level permissions;
- session/CSRF settings;
- `is_staff`/`is_superuser` use;
- custom user/email models;
- allauth/social auth if present.

Pitfalls:

- DRF model/queryset filtering must preserve tenant/object scope;
- permission classes can allow list/create while object checks protect only retrieve/update;
- `is_staff` is often broader/different from business authorization;
- CSRF expectations differ for SessionAuthentication vs bearer-token APIs;
- admin-site privileges should not silently become product admin privileges.

## Flask

Look for Flask-Login/session configuration, Flask-JWT-Extended or similar, CSRF extension, blueprints, decorators, and ORM query helpers.

Pitfalls:

- auth decorator omitted on one blueprint/route;
- signed client cookie assumed to provide server revocation without additional state;
- insecure secret key/default config;
- tenant filters repeated ad hoc instead of repository/service scope.

## Laravel

Look for guards/providers, Sanctum/Passport, policies/gates, middleware, password broker, email verification, Fortify/Jetstream, and Eloquent scopes.

Pitfalls:

- route middleware protects authentication but policy/object authorization is missing;
- mass assignment allows role/tenant/security fields;
- global/local scopes do not consistently apply to exports/jobs;
- token abilities/scopes are defined but not checked at the action;
- queued jobs lose actor/tenant context.

## Rails

Look for Devise, Pundit/CanCanCan, session/cookie config, ActiveRecord scopes, ActiveJob, and controller callbacks.

Pitfalls:

- `before_action` skipped on alternate controller action;
- policy scope missing on collection/list;
- record policy used for one route but not bulk/export;
- strong parameters accidentally permit privileged fields;
- background jobs operate globally without tenant scope.

## Spring Boot / Spring Security

Look for:

- SecurityFilterChain;
- method security (`@PreAuthorize`, etc.);
- OAuth resource-server config;
- password encoder;
- session management;
- CSRF config;
- CORS config;
- JWT decoder/issuer/audience validation;
- repository/service tenant checks.

Pitfalls:

- globally disabling CSRF for a cookie-authenticated browser app without analysis;
- only URL-level roles while service methods can be invoked through other paths;
- authority prefix/mapping confusion;
- JWT decoder verifies signature but audience/application policy is incomplete;
- actuator/admin endpoints not included in intended policy.

## ASP.NET Core

Look for:

- authentication schemes;
- Identity;
- cookie/JWT options;
- authorization policies/requirements/handlers;
- antiforgery;
- Data Protection keys;
- claims transformation;
- EF query filters/tenant scopes.

Pitfalls:

- `[Authorize]` proves authentication but no resource policy;
- default scheme confusion accepts unintended credential type;
- claims from token treated as always-fresh authorization state;
- antiforgery disabled for cookie-authenticated state-changing actions;
- Data Protection key lifecycle inconsistent across replicas.

## Go

Look for router middleware, context identity propagation, session/token libraries, password hashing, and repository scoping.

Pitfalls:

- middleware not attached to all route groups;
- context values populated from decoded but unverified token;
- authorization logic spread across handlers;
- interface/service calls bypass handler guard;
- manually implemented JWT/crypto instead of maintained library.

## GraphQL

Independent of framework:

- authenticate request/connection;
- authorize resolver/resource/field as needed;
- enforce tenant scope in data loaders;
- ensure loaders/cache keys include authorization boundary;
- secure subscriptions;
- control introspection/exposure according to project policy without mistaking obscurity for authorization;
- test nested fields, aliases, fragments, batch operations.

## WebSocket/realtime frameworks

- authenticate handshake/connection;
- authorize each room/channel/topic subscription;
- validate tenant/resource identifier;
- define session expiry/revocation behavior for long-lived connection;
- prevent client-supplied user/tenant identity from becoming trusted socket context;
- test reconnect with revoked credential.

## ORMs and database access

Regardless of ORM:

- inspect whether tenant/owner filters are centralized;
- verify raw SQL paths preserve scope;
- verify admin/reporting queries intentionally bypass or retain tenant filters;
- prevent foreign-key relation injection across tenants;
- protect role/permission/security fields from generic update helpers;
- use transactions for single-use reset/recovery/refresh redemption.

## CI/CD

Add or preserve auth-focused test commands in CI when Stage 07 changes are production-bound.

At minimum ensure the pipeline can detect:

- auth test failures;
- type/build failures;
- migration errors;
- accidental committed secrets through the repository's chosen secret-scanning stage if present.

Do not make Stage 07 depend on a new third-party SaaS scanner when equivalent local tests are sufficient, unless project policy requires it.
