# Passwords, Verification, and Account Recovery

## Contents

- [Purpose](#purpose)
- [Password storage](#password-storage)
- [Password policy](#password-policy)
- [Login response behavior](#login-response-behavior)
- [Password change](#password-change)
- [Password reset token design](#password-reset-token-design)
- [Reset workflow](#reset-workflow)
- [Email/phone verification](#emailphone-verification)
- [Magic links / passwordless email links](#magic-links-passwordless-email-links)
- [Recovery and MFA](#recovery-and-mfa)
- [Recovery destination changes](#recovery-destination-changes)
- [Abuse controls](#abuse-controls)
- [Required negative tests](#required-negative-tests)


## Purpose

Use this reference whenever the application stores password verifiers or provides password reset, magic link, email verification, phone verification, recovery codes, or another account-recovery mechanism.

## Password storage

Use a maintained password-hashing library and a current adaptive password hashing algorithm appropriate to the platform. Follow current OWASP/NIST/framework guidance for parameters rather than copying stale constants from old code examples.

Requirements:

- never store plaintext passwords;
- never store reversibly encrypted passwords merely to support login;
- never use fast general-purpose hashes such as unsalted SHA-family/MD5 as password verifiers;
- use per-password salts through the maintained library;
- if a pepper is used, keep it outside the password database and operate it through a secrets-management mechanism;
- verify passwords through the library's constant-time-aware verification primitive;
- support parameter upgrades/re-hashing when users successfully authenticate if the framework supports it;
- prevent password values from reaching application logs, tracing, analytics, crash reports, or audit metadata.

Benchmark expensive password hashing in the deployment environment so secure parameters do not create an accidental denial-of-service condition. Do not lower parameters merely to make a unit test faster; use test configuration appropriately while production remains secure.

## Password policy

Prefer policies aligned with current NIST/OWASP guidance:

- support long passwords/passphrases;
- do not silently truncate secrets;
- permit broad character sets unless a protocol limitation exists;
- avoid arbitrary composition rules that encourage predictable substitutions unless a governing policy requires them;
- block commonly compromised passwords where practical;
- allow password managers and paste/autofill;
- do not force periodic password rotation without a security reason or governing requirement;
- require password change after evidence of compromise or administrative reset when appropriate.

Verify current official guidance before hard-coding length thresholds in the skill's implementation.

## Login response behavior

Avoid unnecessary account enumeration. Where product UX permits, keep externally observable behavior sufficiently similar for:

- unknown account;
- wrong password;
- suspended/disabled account;
- recovery request for unknown account.

Do not sacrifice operational detection: internal audit telemetry may record the actual reason securely.

## Password change

For an authenticated password change:

- require current password or another recent high-assurance authentication unless the session was created through a trusted recovery flow;
- require step-up for high-risk accounts if policy requires it;
- verify new password policy;
- invalidate active reset tokens;
- decide whether other sessions are revoked, with a secure default for suspected compromise;
- notify the account through an appropriate out-of-band channel when feasible;
- audit success/failure without recording secrets.

## Password reset token design

A reset token should be:

- generated with a cryptographically secure random generator or a maintained framework primitive;
- high entropy and impractical to guess;
- bound to a specific account and purpose;
- short-lived;
- single-use;
- invalidated after successful use;
- invalidated after a newer reset is issued when the design uses a single active reset generation;
- stored as a one-way verifier/hash when feasible so a database read does not reveal a usable reset secret;
- compared safely;
- absent from logs, analytics, referrers, and error tracking;
- transported only over TLS in real environments.

If a token must appear in a URL to support an email link, keep it out of application logging and avoid loading third-party resources on the reset page that could receive the URL/referrer. Exchange the URL token for short-lived server-side reset state as early as practical.

## Reset workflow

A robust flow:

1. User submits account identifier.
2. System returns a generic response regardless of account existence when enumeration resistance is required.
3. Apply per-source and per-account abuse controls without creating a trivial account lockout vector.
4. Generate purpose-bound reset secret.
5. Store only the verifier/metadata needed to validate it.
6. Deliver to the verified recovery channel.
7. Validate token, expiry, purpose, account state, and usage state.
8. Establish a constrained reset transaction; do not treat possession of the link as an unrestricted authenticated session.
9. Set new password using normal password policy and hashing.
10. Mark token consumed atomically.
11. Invalidate competing reset artifacts as designed.
12. Revoke or rotate sessions/refresh credentials according to compromise policy.
13. Emit audit event and notify user.

Use a transaction/atomic update so concurrent requests cannot redeem the same reset token twice.

## Email/phone verification

Verification tokens should follow the same purpose-binding, expiry, single-use, secure-generation, secure-storage, and replay protections as reset tokens.

Additionally:

- bind the token to the exact pending email/phone value;
- invalidate it if that pending value changes;
- do not mark a contact verified merely because another account verified the same string;
- prevent a token issued for one account from being applied to another account;
- avoid auto-granting privileged tenant membership solely from possession of a generic email-verification token.

## Magic links / passwordless email links

Treat a magic link as an authentication credential:

- short lifetime;
- single use;
- purpose and client binding where practical;
- replay protection;
- anti-enumeration request behavior;
- no leakage to logs/analytics/referrers;
- session creation only after successful validation;
- risk controls for high-value operations;
- clear behavior when multiple links are requested.

## Recovery and MFA

Recovery must not silently become the weakest factor in the system.

If MFA is mandatory for an account/role:

- define whether recovery can reset MFA;
- require stronger evidence or administrative review when appropriate;
- audit MFA reset distinctly;
- invalidate remembered-device/session state when warranted;
- notify the user of recovery/MFA reset;
- never reveal full recovery codes after initial display unless the design regenerates them.

Store recovery codes as one-way verifiers when possible. Consume each code atomically and prevent reuse.

## Recovery destination changes

Changing email/phone before recovery can create takeover paths. Require recent authentication and independent verification of the new destination. Consider delaying its eligibility as a recovery destination for high-risk products.

## Abuse controls

Apply controls to:

- login attempts;
- reset requests;
- reset validation;
- resend verification;
- magic link requests;
- OTP verification;
- recovery-code attempts.

Use layered limits so an attacker cannot cheaply target one account from many IPs or lock out arbitrary users from one IP. See `09-abuse-audit-observability.md`.

## Required negative tests

Include as applicable:

- wrong password;
- unknown account response behavior;
- expired reset token;
- already-used reset token;
- reset token for wrong account/purpose;
- concurrent reset redemption;
- old reset token after a new reset generation;
- verification token after pending email/phone changes;
- recovery token after account suspension/deletion;
- reset token leaking into logs test where test tooling can inspect logs;
- MFA account recovery path cannot bypass required assurance.
