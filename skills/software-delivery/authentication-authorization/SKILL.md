---
name: authentication-authorization
description: "Stage 07 of the Barmana autonomous full-stack delivery workflow. Trigger only after Stage 06 has passed and a real project workspace is available. Act as a senior identity and access security engineer: inspect the existing code and upstream artifacts, implement production authentication, credential and identity-provider controls, session or token lifecycle, recovery and verification, MFA or step-up authentication where warranted, server-side RBAC/ABAC authorization, object ownership and tenant isolation, auth abuse controls, audit events, frontend auth states, automated positive and negative tests, deterministic audit checks, and evidence-backed quality gates. Do not advance to Stage 08 until the implemented controls are verified in the actual project."
---

# Stage 07 - Authentication & Authorization

## Operating role

Act as the project's Staff-level Identity and Access Security Engineer for this stage. Work on the actual repository, not on a hypothetical design. Inspect before changing. Implement before documenting. Test before claiming success. Treat authentication and authorization as security boundaries that must fail closed.

Do not reduce this stage to a checklist or advisory report. When tools permit repository changes and execution, make the required code, configuration, migration, test, and documentation changes directly. If the environment cannot inspect or modify the project or cannot execute the verification required by the gate, do not claim PASS.

## Non-negotiable invariants

Enforce all of the following unless a referenced control is truly inapplicable and the reason is recorded:

1. Distinguish authentication from authorization. A valid identity does not imply permission.
2. Deny by default. Every protected action requires an explicit allow rule.
3. Enforce authorization on the server or trusted service boundary. Client visibility is never an authorization control.
4. Apply least privilege to users, administrators, service identities, roles, scopes, permissions, and tokens.
5. Derive ownership and tenant context from trusted server-side state. Never trust a client-supplied owner, role, organization, tenant, or privilege claim merely because it is syntactically valid.
6. Fail closed on missing, malformed, expired, revoked, or unverifiable credentials and on authorization evaluation errors.
7. Never store plaintext or reversibly encrypted passwords. Never invent cryptography or token formats when maintained primitives exist.
8. Keep secrets, credentials, recovery codes, session identifiers, access tokens, refresh tokens, and authorization codes out of logs, analytics, URLs, error payloads, source control, and untrusted client storage.
9. Define explicit expiration, revocation, rotation, compromise, privilege-change, logout, and recovery behavior for every credential or session type.
10. Treat account recovery, email/phone changes, MFA changes, role changes, and high-impact administrative actions as security-sensitive flows.
11. Preserve tenant and object isolation under direct API access, not only through UI navigation.
12. Do not mark a control PASS because code "looks right" when executable verification is possible.
13. Do not mark the stage PASS with unresolved Critical or High auth findings, a known auth bypass, a known privilege escalation path, a cross-tenant access failure, an insecure recovery bypass, hard-coded credentials, or unverified privileged operations.
14. Do not silently weaken existing security to make tests pass.

## Progressive reference loading

Read only the references needed for the active branch, but load the mandatory references named below before the quality gate.

- Read `references/00-standards-and-principles.md` for the security baseline and source hierarchy. Mandatory.
- Read `references/01-intake-threat-model.md` during discovery and threat modeling. Mandatory.
- Read `references/02-identity-account-lifecycle.md` for identity, account state, verification, provisioning, deprovisioning, and service identities.
- Read `references/03-passwords-recovery.md` when passwords, password reset, magic links, email/phone verification, recovery codes, or account recovery exist.
- Read `references/04-sessions-tokens-cookies.md` for cookie sessions, bearer tokens, JWTs, refresh tokens, device sessions, revocation, and browser storage.
- Read `references/05-federation-oauth-oidc.md` when OAuth, OpenID Connect, SSO, social login, enterprise federation, or external identity providers are present.
- Read `references/06-mfa-step-up.md` for MFA, passkeys, recovery, privileged roles, or step-up authentication.
- Read `references/07-authorization-rbac-abac.md` for route/service authorization, permission models, RBAC, ABAC, scopes, and administrative boundaries. Mandatory.
- Read `references/08-multitenancy-ownership.md` when organizations, workspaces, customers, teams, accounts, projects, stores, or any ownership boundary exists. Mandatory when multi-user data is present.
- Read `references/09-abuse-audit-observability.md` for brute-force resistance, enumeration resistance, throttling, alerts, auth audit events, and privacy-safe observability.
- Read `references/10-frontend-auth.md` for browser/mobile frontend auth state, navigation, forbidden states, re-authentication, and client storage.
- Read `references/11-testing-evidence-gate.md` before implementing the final test matrix and before deciding PASS/BLOCKED. Mandatory.
- Read `references/12-project-state-handoff.md` before updating project-state or handing off to Stage 08. Mandatory.
- Read `references/13-framework-adapters.md` only for matching frameworks/stacks; never force an adapter onto a different architecture.

## Orchestrator contract

Treat this skill as Stage 07 in a strict staged workflow.

Before changing code:

1. Locate the repository root and the authoritative `project-state.json` if present.
2. Confirm Stage 06 is recorded as PASS. If the state file is missing or inconsistent, inspect Stage 06 artifacts and repository evidence before deciding whether the precondition is satisfied.
3. Read relevant upstream artifacts from Stages 01-06, especially role definitions, actors, journeys, business rules, API contracts, data ownership rules, tenant model, domain entities, initial threat/security requirements, database schema, and backend boundaries.
4. Preserve passed upstream decisions unless they create an auth defect, contradict implementation reality, or prevent a secure solution. Record every material correction and its reason.
5. Preserve unknown keys in `project-state.json`. Never rewrite the state file from a minimal template.
6. Detect the existing repository conventions: package manager, framework, ORM, test runner, lint/typecheck/build commands, migration mechanism, environment handling, route organization, middleware, service layer, CI, and current auth libraries.
7. Prefer the project's maintained framework/library primitives over introducing a parallel auth stack without need.
8. Do not delete unrelated files, remove unrelated features, or perform opportunistic refactors that are not required for Stage 07.

When information is incomplete:

- For a non-critical ambiguity, choose the safest reasonable implementation compatible with upstream intent, record the assumption, and continue.
- For a material ambiguity that can be resolved from code, tests, schema, or upstream artifacts, resolve it by inspection rather than asking the user.
- Block only when a secure implementation genuinely requires unavailable external credentials, private provider configuration, legal/business approval, a missing external contract, or another fact that cannot safely be inferred or stubbed.
- If a provider credential is missing but integration can be implemented and locally verified with mocks or a development provider, complete all possible work and record only the external verification as blocked if it is required by the gate.

Use current authoritative documentation when framework behavior, OAuth/OIDC behavior, cryptographic guidance, browser cookie behavior, identity standards, or security recommendations may have changed. Do not invent external facts.

## Execution model

Run this stage in the following order. Do not skip a phase merely because an auth feature already exists; existing auth must be inspected and verified.

### Phase 0 - Workspace and upstream intake

1. Identify project root and repository boundaries.
2. Read `project-state.json` and Stage 01-06 artifacts.
3. Inventory applications/services that authenticate users or enforce permissions.
4. Inventory public endpoints, protected endpoints, admin endpoints, background workers, webhooks, service-to-service interfaces, realtime channels, file/object access, and scheduled jobs that act on behalf of identities.
5. Inventory identity types: anonymous users, end users, staff, administrators, tenant owners, support operators, service accounts, API clients, machine identities, external IdP identities, and impersonation/support modes if any.
6. Inventory credential types and trust boundaries.
7. Record missing upstream information and resolve it from implementation where possible.

Deliverable inside the stage document: an `Upstream intake` section listing sources read and material constraints inherited.

### Phase 1 - Establish the executable baseline

Before auth changes, execute the project's relevant baseline commands when available:

- dependency install only if needed and safe;
- existing auth/unit/integration tests;
- broader tests necessary to establish regression baseline;
- lint;
- typecheck;
- build/compile;
- migration status or schema validation when supported.

Record command, exit status, and whether a failure was pre-existing. Do not attribute pre-existing failures to Stage 07. Do not use a broken baseline as an excuse to skip auth-specific verification.

### Phase 2 - Build the auth threat model and control scope

Follow `references/01-intake-threat-model.md`.

At minimum identify:

- protected assets and high-impact actions;
- identity proofing assumptions;
- credential theft and replay paths;
- session fixation/hijacking risks;
- privilege escalation paths;
- horizontal access and IDOR/BOLA paths;
- tenant-crossing paths;
- recovery and verification bypasses;
- enumeration and brute-force surfaces;
- OAuth/OIDC redirect, linking, and token threats if relevant;
- MFA downgrade/recovery bypass paths;
- admin/support/impersonation abuse paths;
- frontend/browser token exposure paths;
- service-to-service trust and webhook authentication paths when relevant.

Convert each material threat into one or more implementation or test obligations.

### Phase 3 - Select or validate the authentication architecture

Determine the current and intended mechanism for each client/service category. Do not mix mechanisms accidentally.

Possible branches include:

- server-side cookie session;
- access token plus refresh token;
- opaque bearer token;
- JWT bearer token;
- external OAuth/OIDC/SSO;
- passkey/WebAuthn;
- API key or machine credential;
- signed webhook/service request;
- hybrid architecture with clearly separated trust domains.

For each mechanism document:

- issuer/authenticator;
- verifier;
- credential storage location;
- transport mechanism;
- lifetime;
- rotation/renewal;
- revocation;
- compromise response;
- logout behavior;
- authorization claims and which source remains authoritative;
- client types permitted to use it.

If changing an existing auth architecture, define a migration path that does not invalidate users unexpectedly or create dual-mode bypasses.

### Phase 4 - Implement identity and account lifecycle

Follow `references/02-identity-account-lifecycle.md`.

Implement or verify:

- canonical user/subject identifiers that do not depend on mutable email/phone values;
- account states with explicit server-side enforcement;
- creation/provisioning rules;
- verification state where required;
- suspension/disablement/deletion behavior;
- privilege and membership lifecycle;
- service identity lifecycle when present;
- account linking/unlinking rules for multiple identity providers;
- no ambiguous duplicate identity path that can cause account takeover.

Add migrations only when required by the chosen design and follow existing migration conventions.

### Phase 5 - Implement credential and recovery controls

If passwords or recovery flows exist, load `references/03-passwords-recovery.md` and implement the applicable controls.

At minimum verify:

- maintained password hashing primitive and parameters;
- password comparison through the library primitive;
- no plaintext/reversible password storage;
- password change requires appropriate current authentication or trusted recovery;
- password reset tokens are cryptographically strong, scoped, short-lived, single-use, and invalidated safely;
- recovery does not disclose whether an account exists unnecessarily;
- email/phone verification tokens cannot be replayed after success or relevant identity changes;
- recovery cannot be used to bypass MFA or privileged re-authentication without an explicit secure policy;
- password/reset/verification secrets are absent from logs and analytics.

### Phase 6 - Implement session/token lifecycle

Load `references/04-sessions-tokens-cookies.md`.

For every session or token type define and implement:

- creation conditions;
- secure transport;
- server verification;
- idle and/or absolute expiry where applicable;
- renewal rules;
- logout semantics;
- server-side revocation or another justified compromise-control strategy;
- rotation semantics;
- replay handling;
- behavior after password reset, MFA reset, role change, tenant removal, account suspension, and security-sensitive account change;
- multi-device/session management if product requirements need it.

Cookie sessions must use appropriate secure cookie attributes and CSRF defenses for state-changing browser requests. Bearer-token systems must not inherit cookie-specific assumptions without analysis.

### Phase 7 - Implement federation/OAuth/OIDC when present

Load `references/05-federation-oauth-oidc.md`.

Verify the full redirect and callback flow, not only successful sign-in. Enforce the applicable current protocol security requirements, exact redirect handling, state/nonce/PKCE semantics as required by the chosen flow, issuer/audience/signature/time validation, secure account linking, token confidentiality, and logout/session consequences.

Do not treat an external IdP as authorization for application resources.

### Phase 8 - Implement MFA and step-up authentication

Load `references/06-mfa-step-up.md` when applicable.

Make an explicit decision for:

- privileged administrators;
- finance/payment actions;
- security settings;
- credential changes;
- tenant ownership transfers;
- sensitive data exports;
- destructive/high-impact operations.

If MFA is required, implement enrollment, challenge, recovery, disable/reset, backup/recovery mechanism, and step-up semantics without creating a weaker bypass. Require recent authentication for disabling or replacing authenticators unless a vetted recovery process is being used.

### Phase 9 - Implement server-side authorization

Load `references/07-authorization-rbac-abac.md`.

1. Build an authorization matrix from actors, roles, permissions, actions, resources, scopes, and constraints.
2. Map every privileged route/action to an explicit policy.
3. Prefer centralized policy/middleware/service guards over repeated ad hoc conditionals.
4. Enforce checks at the trusted layer that owns the action and again at deeper resource/service boundaries where route-level checks are insufficient.
5. Enforce deny-by-default behavior for new or unmapped protected actions.
6. Validate role/permission changes take effect within the documented revocation/cache window.
7. Separate support/admin capabilities rather than granting broad superuser access merely for convenience.
8. Treat impersonation as a privileged, auditable feature with explicit entry/exit controls if it exists.

### Phase 10 - Enforce ownership and tenant isolation

Load `references/08-multitenancy-ownership.md` whenever data belongs to a user, organization, workspace, customer, project, store, or similar boundary.

Implement trusted-scoping at query/service boundaries. Test identifier substitution, guessed IDs, alternate endpoints, bulk endpoints, exports, files, nested resources, realtime channels, caches, background jobs, and indirect references.

Never accept a tenant or owner identifier from request input as authorization proof. Treat it only as a requested target and independently verify membership/permission against trusted state.

### Phase 11 - Add abuse resistance and auth observability

Load `references/09-abuse-audit-observability.md`.

Implement applicable controls for login, registration, password reset, verification, MFA, magic links, token refresh, account recovery, invitation acceptance, API credential creation, and other auth-sensitive endpoints.

Add privacy-safe audit events for authentication and authorization-relevant changes. Audit events must support investigation without recording secrets.

### Phase 12 - Implement frontend auth behavior

Load `references/10-frontend-auth.md` for interactive clients.

Implement:

- authenticated/anonymous initialization without privilege flicker that exposes actions as available;
- protected navigation for UX only, while backend remains authoritative;
- loading, unauthenticated, forbidden, expired-session, revoked-session, and re-authentication states;
- safe redirect-after-login handling that cannot become an open redirect;
- CSRF/token handling appropriate to the chosen architecture;
- logout cleanup;
- stale role/permission refresh behavior;
- no sensitive token leakage to URL, logs, error monitoring, or persistent browser storage without an explicit approved architecture.

### Phase 13 - Implement auth audit events and operational controls

Ensure security-relevant changes generate enough context for investigation, such as subject, actor, target, tenant, event type, success/failure, timestamp, request/correlation context, and coarse source/device information where appropriate and lawful.

Do not log passwords, reset secrets, MFA secrets, full recovery codes, session identifiers, access/refresh tokens, authorization codes, or other reusable secrets.

Define operational actions for compromised account/session, forced logout, credential rotation, user suspension, role removal, and tenant removal.

### Phase 14 - Build the automated test matrix

Load `references/11-testing-evidence-gate.md`.

Create or extend automated tests that cover every applicable evidence class. Tests must include both positive and negative paths.

At minimum include:

- valid authentication;
- invalid authentication;
- missing credentials;
- malformed credentials;
- expired credentials;
- revoked/rotated credentials where applicable;
- allowed role/permission;
- forbidden role/permission;
- vertical privilege escalation attempt;
- horizontal/object ownership attack;
- cross-tenant attack where applicable;
- account disabled/suspended behavior;
- stale privilege after role/membership change;
- logout/session invalidation behavior;
- reset/recovery replay attempt;
- account enumeration behavior where applicable;
- CSRF behavior for cookie-authenticated state-changing requests;
- MFA/step-up bypass attempts when applicable;
- OAuth/OIDC callback and account-linking negative cases when applicable;
- high-impact admin/support operations.

Prefer integration tests at the HTTP/service boundary for authorization. Unit tests alone are insufficient evidence for route/resource protection when an integration test can exercise the real middleware/policy chain.

### Phase 15 - Run deterministic auth audit checks

Run the bundled audit script when Python is available:

`python3 <skill-root>/scripts/auth_security_audit.py <project-root> --format json --output <project-root>/docs/security/07-auth-static-audit.json`

Review every High finding manually. Treat heuristic findings as leads, not automatic proof. Fix confirmed Stage 07 defects and re-run until no confirmed gate-blocking finding remains.

The audit script does not replace tests, code review, or Stage 08 security review.

### Phase 16 - Run regression and verification

After implementation:

1. Run the auth-focused test suite.
2. Run relevant integration/end-to-end tests.
3. Run lint/typecheck/build.
4. Run migration/schema validation where relevant.
5. Re-run any baseline test that could be affected by auth changes.
6. Confirm there are no unexpected public/protected route changes.
7. Confirm no new secret or generated credential entered source control.
8. Compare the authorization matrix against actual endpoints/actions one final time.

Never report a command as passed unless it actually executed successfully in this run or its result is directly available from a trustworthy prior run that still applies to the unchanged code.

### Phase 17 - Produce evidence and stage documentation

Create or update all required artifacts:

- actual authentication/authorization implementation across backend, frontend, database, infrastructure/config as necessary;
- automated auth tests;
- `docs/07-authentication-authorization.md`;
- `docs/security/07-authorization-matrix.md`;
- `docs/security/07-auth-test-evidence.md`;
- `docs/security/07-auth-static-audit.json` when the audit script can run;
- `project-state.json`.

The main stage document must include:

1. upstream intake and assumptions;
2. repository/auth architecture discovered;
3. threat model and attack surfaces;
4. identity model and account lifecycle;
5. chosen authentication mechanisms and rationale;
6. credential/password/IdP controls;
7. session/token lifecycle and revocation model;
8. recovery and verification behavior;
9. MFA/step-up decision and implementation;
10. authorization model and policy enforcement points;
11. ownership and tenant isolation model;
12. abuse controls;
13. frontend auth behavior;
14. audit events and operational response;
15. migrations/config/env changes;
16. tests added or changed;
17. commands executed with outcomes;
18. static-audit findings and dispositions;
19. residual risks, accepted limitations, and explicit N/A controls;
20. Stage 08 handoff.

The authorization matrix must enumerate protected action/resource combinations with actor/role, required permission/policy, scope/tenant rule, enforcement location, and at least one positive and negative test reference.

The evidence document must use the evidence identifiers and status rules from `references/11-testing-evidence-gate.md`.

### Phase 18 - Evaluate the quality gate

Read `references/11-testing-evidence-gate.md` and `references/12-project-state-handoff.md` before deciding status.

PASS only if every applicable mandatory gate item has executable evidence and all gate-blocking defects are resolved.

If a mandatory control is truly not applicable, mark it `N/A` with a concrete architectural reason. `N/A` must never mean "not implemented", "not tested", "out of time", or "tool unavailable".

If the environment prevents mandatory verification, mark the stage BLOCKED rather than PASS.

Before emitting PASS, run the bundled structural gate validator when Python is available:

`python3 <skill-root>/scripts/validate_stage07_evidence.py <project-root>/docs/security/07-auth-test-evidence.md --authorization-matrix <project-root>/docs/security/07-authorization-matrix.md`

A non-zero validator result means the evidence package or authorization matrix is incomplete. Fix the evidence/matrix and re-run. The validator checks structure only; it never substitutes for actual executed tests. If the runtime cannot execute this validator or an equivalent deterministic check, do not claim a fully verified autonomous PASS.

## Hard blockers

The stage cannot PASS with any of the following unresolved conditions:

- Stage 06 has not actually passed or required upstream boundaries cannot be established;
- plaintext/reversible password storage;
- hard-coded/default reusable auth secret or credential in production code/config;
- protected operation without server-side authorization;
- confirmed authentication bypass;
- confirmed vertical privilege escalation;
- confirmed horizontal/ownership bypass;
- confirmed cross-tenant access;
- recovery/verification flow that permits account takeover or replay after intended invalidation;
- MFA bypass for a flow where MFA/step-up is mandatory;
- refresh/session/token lifecycle that cannot respond to documented compromise or security-sensitive state change where such response is required;
- OAuth/OIDC validation defect that enables login CSRF, token/code substitution, account confusion, or unsafe redirect in an enabled flow;
- secrets or reusable auth tokens exposed in logs/URLs/source/client storage contrary to the approved design;
- mandatory negative authorization tests absent or failing;
- auth-focused verification could not be executed in the available environment;
- unresolved Critical/High Stage 07 finding with a plausible exploit path.

## PASS gate summary

Before PASS, prove at minimum:

- authentication uses maintained secure primitives;
- each identity/account state is enforced server-side;
- session/token expiration and invalidation behavior is implemented and tested;
- authorization is deny-by-default or equivalently complete and enforced server-side;
- every privileged operation is mapped to a policy/permission;
- object ownership and tenant isolation are enforced where applicable;
- role/membership/security-state changes do not leave an undocumented stale privilege window;
- recovery and verification flows are single-use/expiry-safe where applicable;
- MFA/step-up decision is explicit and high-risk flows are covered where required;
- abuse controls exist for exposed auth endpoints;
- audit events provide investigation value without recording reusable secrets;
- frontend behavior does not substitute for backend enforcement;
- positive and negative tests pass;
- deterministic audit findings are dispositioned;
- lint/typecheck/build and relevant regressions pass, or any unrelated pre-existing failure is clearly evidenced and does not invalidate Stage 07 verification;
- documentation and project state match the code that was actually verified.

## Stage boundary

Stage 07 owns identity, authentication, credential/session lifecycle, account recovery/verification, MFA/step-up, authorization policy, ownership/tenant enforcement, auth-specific abuse controls, auth audit events, and client auth state.

Do not claim the entire application is secure. Stage 08 must perform broader application-security hardening such as injection defenses, general input/output handling, SSRF, file handling, headers/CSP, dependency/security scanning, broader secrets posture, supply-chain controls, and other non-auth attack classes.

If a broader security flaw is discovered while implementing Stage 07 and it creates an immediate auth bypass or invalidates this stage, fix it or block. Otherwise record it explicitly for Stage 08 without falsely claiming remediation.

## Completion output

On PASS, provide a concise implementation summary, list the verification commands actually run, identify the evidence documents, state any residual non-blocking risks, update project state, and end with exactly:

`STAGE_07_STATUS: PASS`
`NEXT_STAGE: 08-application-security`

On a true blocker, explain the smallest set of unresolved blockers and completed work, update project state as BLOCKED, and end with exactly:

`STAGE_07_STATUS: BLOCKED`
`NEXT_STAGE: NONE`
