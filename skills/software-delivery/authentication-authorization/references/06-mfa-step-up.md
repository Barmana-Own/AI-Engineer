# MFA, Passkeys, Recovery, and Step-Up Authentication

## Contents

- [Purpose](#purpose)
- [Risk decision](#risk-decision)
- [Authenticator preference](#authenticator-preference)
- [Enrollment](#enrollment)
- [Challenge](#challenge)
- [Step-up state](#step-up-state)
- [Recovery codes](#recovery-codes)
- [Disable or replace MFA](#disable-or-replace-mfa)
- [Lost-factor recovery](#lost-factor-recovery)
- [Remembered devices](#remembered-devices)
- [Administrative MFA reset](#administrative-mfa-reset)
- [Required tests](#required-tests)


## Purpose

Use this reference to decide where additional authentication assurance is needed and to implement the full lifecycle, not only the challenge screen.

## Risk decision

Evaluate MFA/step-up for:

- administrators and privileged operators;
- production/infrastructure controls;
- finance/payment/refund/payout actions;
- API key/secret creation;
- role or membership administration;
- security settings;
- password/email/phone/authenticator changes;
- bulk data export;
- tenant ownership transfer;
- destructive actions with broad impact;
- impersonation;
- high-value account recovery.

Record `required`, `optional`, or `not applicable` for each high-risk action, with rationale.

## Authenticator preference

Prefer phishing-resistant authenticators such as passkeys/WebAuthn for high-risk use when the product and client environment support them. TOTP can be appropriate but is phishable. SMS/voice factors have additional interception/SIM-swap risks and should not be treated as equivalent to phishing-resistant authentication.

Follow current NIST/provider/platform guidance for assurance-sensitive deployments.

## Enrollment

Secure enrollment requires:

- authenticated session;
- recent authentication/step-up before adding a new authenticator for high-risk accounts;
- server-generated challenge/secret through a maintained library/protocol;
- proof that the new authenticator works before marking enrollment complete;
- recovery mechanism setup when policy requires it;
- audit event and user notification where appropriate;
- no secret in logs/analytics.

For TOTP, protect the seed as a credential. Limit QR/seed exposure to the enrollment transaction and store it according to the threat model, typically encrypted at rest because the server must verify future codes.

For WebAuthn/passkeys, validate relying-party ID/origin/challenge/user binding through a maintained implementation.

## Challenge

Define:

- which actions require MFA;
- how long a successful challenge remains fresh;
- whether assurance applies to the whole session or a specific action;
- allowed authenticator types;
- retry limits/backoff;
- replay prevention;
- device/session binding where applicable.

Do not rely on a client boolean such as `mfaVerified=true` without server-verifiable state.

## Step-up state

Represent recent authentication/step-up using trusted server/session state or a narrowly scoped signed assertion with explicit lifetime and audience/action context.

Test expiration and reuse across actions/users/tenants.

## Recovery codes

- generate high-entropy one-time codes;
- display only at creation/regeneration unless policy deliberately supports retrieval;
- store one-way verifiers when possible;
- consume atomically;
- prevent reuse;
- support regeneration that invalidates prior codes;
- audit use and regeneration;
- notify user after recovery-code use when appropriate.

## Disable or replace MFA

Disabling/replacing an authenticator is a privileged security event.

Require:

- recent high-assurance authentication or approved recovery process;
- explicit authorization for administrative resets;
- audit event;
- user notification where feasible;
- invalidation of remembered-device/step-up state as policy requires;
- session review/revocation for suspected compromise.

Do not allow an attacker with only a stolen session to silently remove the factor that would otherwise stop them.

## Lost-factor recovery

Define a recovery hierarchy. Possible methods include:

- another enrolled phishing-resistant authenticator;
- recovery code;
- verified secondary factor;
- organization administrator-assisted process;
- support/manual identity proofing for high-risk products.

Do not add weak security questions as a default recovery factor.

Recovery should not create a permanent downgrade. After recovery, require re-enrollment or a controlled security review as appropriate.

## Remembered devices

If supported:

- use a dedicated revocable token, not a permanent bypass flag;
- set explicit lifetime;
- bind to account/session context;
- revoke on password/MFA reset or compromise;
- expose device/session management if product requirements justify it;
- do not treat remembered-device state as sufficient for the highest-risk actions unless policy explicitly allows it.

## Administrative MFA reset

If support/admin can reset a user's MFA:

- require a dedicated permission;
- require step-up for the operator;
- record actor, target, tenant, reason, and result;
- notify the user;
- consider delay/approval for especially high-value accounts;
- revoke affected sessions according to compromise policy.

## Required tests

As applicable:

- protected action denied before challenge;
- protected action allowed after valid challenge;
- step-up expires;
- challenge state cannot be replayed for another account/action;
- wrong/replayed TOTP or WebAuthn challenge rejected;
- recovery code single-use;
- MFA disable requires recent authentication;
- remembered-device token revoked after MFA reset;
- lower-assurance recovery cannot silently bypass mandatory high-assurance policy;
- admin MFA reset requires dedicated permission and audit event.
