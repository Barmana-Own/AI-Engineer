# Severity and Finding Policy

## Contents

- Priority vs severity
- Critical / High / Medium / Low / Info
- Confidence
- Finding schema
- Blocking rules
- Risk acceptance

Use one severity model consistently across functional, reliability, security and release findings.

## Priority vs severity

- **Severity** describes impact if the defect occurs.
- **Priority** describes release urgency.

Map release blockers conservatively:
- P0: release-stop emergency; catastrophic or immediately exploitable critical impact.
- P1: must fix before release; High/Critical security, broken core requirement, data-loss risk, auth bypass, failed required build/migration/test.
- P2: important but may be non-blocking when scoped/documented and not part of a core journey.
- P3: low-risk quality/debt/documentation polish.

## Severity definitions

### Critical
Use when a defect can reasonably cause one or more of:
- broad unauthorized privileged access;
- remote code execution in intended deployment;
- exposure of highly sensitive secrets/data at broad scale;
- destructive production data loss/corruption with no practical safeguard;
- complete compromise of trust boundaries.

Critical is P0/P1 and always blocks.

### High
Use when a defect can reasonably cause:
- privilege escalation or cross-tenant/object access with meaningful impact;
- authentication/session bypass;
- serious sensitive data exposure;
- reliable corruption/loss of important data;
- core business flow failure for a substantial user class;
- known exploitable high-risk dependency on a reachable path;
- inability to build/start/migrate the production release.

High is normally P1 and blocks.

### Medium
Use for meaningful defects with constrained impact or exploitation conditions, such as:
- authorization weakness with limited scope;
- reliability bug with recoverable impact;
- missing rate/abuse control on a sensitive but constrained path;
- stale documentation likely to cause deployment error;
- partial non-core feature failure.

Medium may block when it affects a core requirement, compliance obligation, or safe operation.

### Low
Use for low-impact hardening/usability/maintainability defects that do not compromise core release behavior.

### Info
Use for observations, debt, optional hardening, or evidence notes without a demonstrated defect.

## Confidence

Record confidence separately:
- `CONFIRMED` — reproduced or directly proven by source/runtime evidence.
- `HIGH` — strong evidence with minimal uncertainty.
- `MEDIUM` — plausible and evidence-backed but not fully reproduced.
- `LOW` — candidate requiring further verification.

Never label a regex secret hit as CONFIRMED until the value/context is inspected safely.

## Finding schema

Each finding should contain:
- stable ID, e.g. `AUTH-001`, `DATA-002`, `REL-003`;
- title;
- category;
- severity;
- priority;
- confidence;
- blocking boolean;
- affected requirement/journey;
- owning stage;
- evidence;
- root cause;
- user/business/technical impact;
- reproduction or inspection steps;
- remediation plan;
- status: OPEN / REPAIRED_PENDING_VERIFY / CLOSED / ACCEPTED_NONBLOCKING / FALSE_POSITIVE;
- repair references and verification evidence.

## Blocking rules

Always block on:
- any open Critical;
- any open High security finding;
- authn/authz bypass regardless of label;
- broken or missing core requirement;
- known data-loss/corruption path affecting normal operation;
- failed required build/test/migration/startup;
- real secret/private production data intended for delivery;
- intentional production bypass of auth/validation/test controls;
- a P0/P1 finding.

A Medium can block when it affects a core journey or safe production operation.

## Risk acceptance

Do not self-accept a blocking risk. Only downgrade to non-blocking when:
1. impact is genuinely below blocking threshold; or
2. explicit authorized risk acceptance exists and release policy allows that class to be accepted.

Even when accepted, record scope, rationale, owner, and expiry/revisit condition when available.
