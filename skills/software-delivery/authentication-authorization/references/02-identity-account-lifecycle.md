# Identity and Account Lifecycle

## Contents

- [Purpose](#purpose)
- [Canonical subject identity](#canonical-subject-identity)
- [Account states](#account-states)
- [Registration/provisioning](#registrationprovisioning)
- [Membership lifecycle](#membership-lifecycle)
- [Privilege lifecycle](#privilege-lifecycle)
- [Account linking](#account-linking)
- [Email/phone changes](#emailphone-changes)
- [Deactivation and deletion](#deactivation-and-deletion)
- [Service identities](#service-identities)
- [Impersonation/support access](#impersonationsupport-access)
- [Required tests](#required-tests)


## Purpose

Use this reference to implement identities as explicit security objects with deterministic lifecycle behavior.

## Canonical subject identity

Use an immutable internal subject/user identifier as the primary security identity. Do not use email address, phone number, username, tenant slug, display name, or external provider email as the sole immutable internal key unless the system formally guarantees immutability and uniqueness.

For external providers, store provider identity using a stable provider identifier plus provider subject identifier. Treat display/email claims as attributes, not primary proof of account equivalence unless the provider and linking policy justify it.

## Account states

Define only the states the product needs, but make them explicit. Common examples:

- pending/unverified;
- active;
- locked or temporarily restricted;
- suspended;
- disabled;
- invited;
- deletion-pending;
- deleted/closed.

For every state define:

- can authenticate?;
- can refresh session/token?;
- can access existing sessions?;
- can receive recovery/verification?;
- can be added to a tenant?;
- can retain API keys/service credentials?;
- what audit event is emitted on transition?;
- who/what may trigger the transition?;
- whether the transition invalidates sessions or credentials.

Enforce states on the server at authentication and/or authorization boundaries. A UI badge is not enforcement.

## Registration/provisioning

For public registration:

- validate uniqueness rules safely;
- prevent privileged fields from being client-controlled;
- avoid assigning elevated default roles;
- treat verification state independently from account creation;
- decide whether an unverified account may authenticate and what it may access;
- apply rate/abuse controls;
- prevent invitation or tenant-join flows from granting privileges outside the intended scope.

For administrator provisioning:

- require an explicit privileged permission;
- audit actor, target, tenant, granted role, and result;
- do not accept arbitrary role names/permission sets without policy validation.

For SCIM/enterprise provisioning or directory sync, follow provider protocol requirements and define deprovisioning behavior explicitly.

## Membership lifecycle

If organizations/tenants/workspaces exist, separate global account state from membership state.

A user can be globally active but removed from one tenant. Tenant membership checks must not rely solely on global authentication.

Define:

- invite created;
- invite accepted;
- membership active;
- role changed;
- membership suspended;
- membership removed;
- tenant ownership transfer;
- tenant disabled/deleted.

Each transition must define session/token/cache consequences.

## Privilege lifecycle

When role/permission/membership changes:

- decide how quickly the change must affect active sessions;
- invalidate or refresh cached authorization context within that bound;
- prevent an access token with stale elevated claims from remaining valid longer than the accepted risk window;
- test both privilege grant and privilege removal;
- audit the actor and target.

Privilege removal is usually more security-sensitive than privilege grant propagation latency.

## Account linking

When one account can link multiple authenticators or identity providers:

- require a trusted existing session plus recent authentication for linking when feasible;
- verify the new authenticator/provider identity independently;
- do not auto-link solely because email strings match unless the provider trust model and product policy explicitly allow it;
- prevent linking to an identity already bound to another account unless a controlled merge process exists;
- audit link and unlink operations;
- ensure at least one valid recovery/authentication path remains after unlinking;
- require stronger proof before unlinking the last high-assurance authenticator.

## Email/phone changes

Treat primary email/phone changes as security-sensitive because they often control recovery.

Define:

- recent-authentication requirement;
- verification of the new destination;
- whether confirmation from the old destination is required for high-risk accounts;
- notification to the old destination when appropriate;
- reset/recovery token invalidation after the change;
- session invalidation or step-up consequences;
- cooldown or risk review for especially sensitive actions if needed.

## Deactivation and deletion

On suspension/disablement:

- prevent new authentication;
- prevent refresh/renewal;
- revoke active server-side sessions/refresh credentials according to policy;
- disable relevant API/service credentials;
- remove tenant access as required;
- preserve necessary audit records under project policy.

On deletion:

- distinguish authentication identity deletion from data-retention/legal deletion policy;
- prevent subject ID reuse if it could confuse audit or ownership history;
- revoke credentials and sessions;
- handle external provider links and API credentials.

## Service identities

Do not model service identities as ordinary human admin users unless the architecture deliberately requires it.

For machine credentials:

- assign a distinct identity type;
- use least-privilege scopes/permissions;
- support rotation and revocation;
- record creation/last-use/owner metadata when feasible;
- avoid interactive recovery features;
- never expose secret material again after creation unless the credential type specifically supports it;
- hash stored API keys when verification can be performed by hashing the presented key;
- distinguish credential ID/prefix from secret value.

## Impersonation/support access

If support/admin impersonation exists:

- require a dedicated permission;
- require recent authentication or step-up for high-risk contexts;
- record both real actor and effective subject;
- display clear UI state to the operator;
- prevent silent privilege expansion beyond the impersonated subject unless explicitly designed;
- provide explicit exit semantics;
- log start/end/reason/target/tenant;
- consider prohibiting selected sensitive actions while impersonating.

## Required tests

At minimum test:

- inactive account denied;
- suspended account denied or restricted as designed;
- tenant-removed user denied despite valid global session;
- role removal becomes effective inside documented window;
- account linking cannot hijack another account;
- email/phone change does not leave stale recovery token valid when it should not;
- service credential cannot exceed its scope;
- impersonation requires the dedicated permission if implemented.
