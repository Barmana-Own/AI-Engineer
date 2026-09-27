# Frontend Authentication and Authorization UX

## Contents

- [Purpose](#purpose)
- [Auth state machine](#auth-state-machine)
- [Protected navigation](#protected-navigation)
- [Permission-aware UI](#permission-aware-ui)
- [401 vs 403 behavior](#401-vs-403-behavior)
- [Refresh concurrency](#refresh-concurrency)
- [Client storage](#client-storage)
- [Redirect handling](#redirect-handling)
- [CSRF integration](#csrf-integration)
- [MFA/step-up UX](#mfastep-up-ux)
- [Account/recovery UX](#accountrecovery-ux)
- [Admin/support UX](#adminsupport-ux)
- [Error handling](#error-handling)
- [Required tests](#required-tests)


## Purpose

Use this reference for browser/mobile clients. Frontend behavior supports security and usability but never replaces server enforcement.

## Auth state machine

Model explicit states rather than a single `isLoggedIn` boolean when the product needs them.

Common states:

- initializing/unknown;
- anonymous;
- authenticating;
- authenticated;
- authenticated but verification required;
- MFA/step-up required;
- forbidden;
- session expired/revoked;
- account suspended/disabled;
- recovery flow;
- error/offline where relevant.

Avoid rendering privileged actions as usable before authoritative auth state loads.

## Protected navigation

Frontend route guards may improve UX by redirecting anonymous users or hiding unavailable pages. They are not security controls.

Always assume an attacker can call APIs directly.

## Permission-aware UI

Use server-provided or trusted-session permission context to decide what to show. Do not infer authorization from editable local data.

If permission state becomes stale:

- handle server `401`/`403` responses correctly;
- refresh session/permission state when the architecture supports it;
- do not retry forbidden requests in a loop;
- remove stale privileged UI after role/membership revocation.

## 401 vs 403 behavior

Use a consistent client policy:

- `401`/equivalent: authentication missing/invalid/expired; attempt safe refresh only if architecture supports it, otherwise transition to re-authentication.
- `403`/equivalent: identity is known but action is not allowed; show forbidden state and do not redirect into an infinite login loop.

Actual API semantics may vary; align frontend behavior with backend contract.

## Refresh concurrency

For refresh-token architectures:

- prevent many simultaneous failed API requests from causing many concurrent refresh requests;
- serialize/single-flight refresh where appropriate;
- avoid retry loops when refresh is invalid/revoked;
- clear auth state deterministically after terminal refresh failure;
- replay original requests only when safe and intended.

## Client storage

- keep reusable bearer secrets out of persistent JavaScript-readable storage when architecture can avoid it;
- never store password, MFA seed, recovery code, client secret, or raw API key after initial display/entry;
- do not place tokens in URL/query/hash unless the protocol explicitly requires a transient value and the flow prevents leakage;
- clear local sensitive state on logout but rely on server invalidation for actual revocation.

## Redirect handling

After login/logout/recovery:

- prefer safe relative internal paths;
- validate any user-controlled return destination;
- reject protocol-relative/external schemes unless explicitly allowlisted;
- avoid carrying access tokens in redirect URLs;
- preserve only non-sensitive intended navigation state.

Test open-redirect payloads.

## CSRF integration

For cookie-authenticated browser apps:

- include framework-required CSRF token on state-changing requests;
- refresh token when session rotation requires it;
- handle CSRF rejection distinctly from generic auth failure if needed;
- never disable CSRF globally to simplify API calls.

For bearer-token architectures, analyze CSRF based on whether credentials are automatically attached by the browser rather than copying cookie assumptions.

## MFA/step-up UX

- distinguish login MFA from action-specific step-up;
- preserve intended action safely across challenge;
- expire step-up state server-side;
- do not let frontend-only timers decide assurance;
- handle unavailable/lost authenticator through approved recovery path;
- do not expose TOTP seed/recovery code after setup except through explicit regeneration policy.

## Account/recovery UX

- use generic reset request response when enumeration resistance is required;
- avoid exposing whether email/phone belongs to an account in public flows unless policy accepts it;
- do not put reset secrets into analytics page titles/events;
- prevent third-party scripts/resources on sensitive recovery pages from receiving token-bearing URLs/referrers where feasible;
- after password/MFA change, reflect server session invalidation correctly.

## Admin/support UX

- show active tenant/context clearly;
- separate global and tenant administration;
- display impersonation state prominently;
- require confirmation/step-up for high-impact actions as backend policy requires;
- avoid pre-filling or exposing secrets;
- show API key secret only at creation if the backend cannot retrieve it again.

## Error handling

Do not expose:

- raw token verification errors;
- stack traces;
- password hash details;
- whether a specific secret/key matched;
- internal role policy implementation details that aid bypass.

Provide stable user-facing errors and detailed server-side telemetry.

## Required tests

As applicable:

- anonymous protected route UX;
- 401 transition to refresh/re-login;
- 403 forbidden state;
- refresh single-flight behavior;
- terminal refresh failure clears auth state;
- open redirect blocked;
- stale role removal updates UI after server denial/state refresh;
- logout clears local state and server rejects prior credential according to policy;
- CSRF token included/rejected correctly;
- MFA step-up cannot be bypassed by direct navigation/client state edit.
