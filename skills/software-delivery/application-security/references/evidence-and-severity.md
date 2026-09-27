# Evidence, Finding Lifecycle, Severity, and Structured Ledger

## Table of contents

1. Finding identity
2. Confidence model
3. Finding status model
4. Evidence requirements
5. Severity rubric
6. Residual risk
7. Root-cause and duplicate handling
8. JSON ledger schema
9. Examples of correct disposition

## 1. Finding identity

Assign stable IDs in discovery order: `SEC-001`, `SEC-002`, etc. Do not create a new ID merely because remediation changed the affected line number. A single root cause affecting many endpoints may be one systemic finding with an affected-surface list; separate findings when root causes, owners, severity or remediation differ materially.

## 2. Confidence model

Use exactly one:

- `CONFIRMED`: direct code/data-flow proof, deterministic failing security test, or safe reproducible authorized runtime evidence establishes the issue.
- `STRONG`: concrete reachable code/configuration evidence strongly supports the issue, but a runtime/environment dependency prevents complete confirmation.
- `SUSPECTED`: plausible candidate with incomplete source/sink/reachability/control evidence. Do not present as a confirmed vulnerability.
- `FALSE_POSITIVE`: investigated evidence shows the candidate does not violate the security invariant.

Scanner output alone is `SUSPECTED` at most.

## 3. Finding status model

Use exactly one:

- `OPEN`: confirmed/strong issue not yet being fixed.
- `IN_REMEDIATION`: code/test work is underway.
- `FIXED`: remediation is applied and the original condition was retested successfully.
- `RESIDUAL_RISK`: issue remains partially/unfixed with explicit rationale, compensating controls and follow-up owner. Critical/High residual risk prevents PASS unless the issue is genuinely outside project control and the gate is BLOCKED.
- `BLOCKED`: remediation or confirmation requires a genuine unavailable external dependency.
- `FALSE_POSITIVE`: candidate disproved.

Do not create `ACCEPTED_RISK` autonomously. Only record stakeholder risk acceptance if the user or an authorized project artifact explicitly supplies it; even then, preserve the underlying technical severity and who accepted it.

## 4. Evidence requirements

Every material finding must record:

- security invariant violated;
- affected component/endpoint/job;
- exact code/config location when available;
- untrusted source or attacker-controlled decision point;
- sensitive sink/action/asset;
- existing controls and why they fail;
- actor/role/tenant prerequisites;
- reachability/exposure;
- concise proof or reproduction method;
- observed vs expected behavior when runtime-tested;
- impact;
- root cause;
- remediation;
- regression test;
- retest result.

Evidence must be reproducible by another engineer without exposing real secrets or harmful customer data.

For HTTP evidence, record method/path, actor class, relevant redacted headers/parameters, response status and the minimal response property proving the issue. Do not store full sensitive bodies.

For source evidence, record file and line/range when possible plus a short explanation of the control/data flow. Do not paste large source blocks unnecessarily.

## 5. Severity rubric

Determine severity from the combination of impact, exploitability and exposure. Consider compensating controls, required privilege and tenant blast radius. Do not use labels mechanically.

### Critical

Typical characteristics:

- unauthenticated or low-privilege remote code execution in a meaningful deployment path;
- systemic authentication bypass or token forgery leading to broad account takeover;
- compromise of signing/encryption/master credentials enabling broad control;
- cross-tenant or platform-wide sensitive-data compromise with minimal prerequisites;
- direct destructive financial/state manipulation at broad scale;
- a chain that gives equivalent catastrophic impact.

Critical requires a high-confidence and severe real-world path, not merely use of a dangerous API.

### High

Typical characteristics:

- exploitable BOLA/IDOR exposing or modifying sensitive records across users/tenants;
- vertical privilege escalation to administrative/sensitive functions;
- account takeover through broken recovery/session lifecycle;
- serious injection with meaningful data/control impact;
- stored XSS in a privileged/high-impact context;
- SSRF reaching sensitive internal/cloud control surfaces under realistic conditions;
- exposed live production secrets with meaningful privilege;
- payment/business-state manipulation with substantial impact;
- public sensitive private-object exposure.

### Medium

Typical characteristics:

- meaningful weakness with additional prerequisites, constrained scope or strong compensating controls;
- limited information exposure;
- CSRF on a state-changing operation with constrained impact;
- reflected XSS with realistic but limited impact;
- missing rate/abuse controls on an expensive or sensitive endpoint where immediate exploitation is constrained;
- weak hardening that materially increases likelihood/impact of another defect.

### Low

Typical characteristics:

- defense-in-depth gaps with low direct impact;
- low-sensitivity information leakage;
- missing hardening header where no higher-impact path is demonstrated;
- minor configuration weakness with narrow exposure.

### Info

Use for observations, secure-design improvements, inventory notes and controls verified. Do not use Info to bury an actual exploitable defect.

### Severity adjustment questions

Before finalizing severity, answer:

- Is authentication required? What privilege?
- Is user interaction required?
- Is the path internet-exposed or internal/local only?
- Is exploitation deterministic or highly conditional?
- What data/action can actually be reached?
- Is impact one object, one tenant, many tenants, or platform-wide?
- Are meaningful compensating controls present?
- Does exploitation require a separate vulnerability?

## 6. Residual risk

A residual-risk entry must contain:

- remaining technical weakness;
- reason not fully remediated;
- affected scope;
- compensating controls;
- probability/impact rationale;
- named role/owner for follow-up if known;
- concrete next action;
- target stage/release if known.

Stage 08 may PASS with a Medium residual risk only when it is well-bounded, not a hidden High, compensating controls are meaningful, and the report makes the limitation explicit. Critical/High within project control cannot remain for PASS.

## 7. Root-cause and duplicate handling

Group duplicates when many endpoints share the same broken shared middleware/policy. Still enumerate affected surfaces. After fixing a shared root cause, test representative and highest-risk affected paths plus a boundary matrix rather than assuming all paths are fixed.

Do not group findings merely because they share an OWASP category if their code paths and remediation differ.

## 8. JSON ledger schema

Create `docs/security/08-security-findings.json` with this shape:

```json
{
  "stage": "08-application-security",
  "generated_at": "ISO-8601 timestamp",
  "gate_status": "PASS|FAIL|BLOCKED",
  "scope": {
    "repository": "relative or logical project identifier",
    "active_testing": "summary of authorized dynamic scope",
    "excluded": ["third-party or unauthorized targets"]
  },
  "findings": [
    {
      "id": "SEC-001",
      "title": "Short root-cause-oriented title",
      "severity": "Critical|High|Medium|Low|Info",
      "confidence": "CONFIRMED|STRONG|SUSPECTED|FALSE_POSITIVE",
      "status": "OPEN|IN_REMEDIATION|FIXED|RESIDUAL_RISK|BLOCKED|FALSE_POSITIVE",
      "component": "service/module/endpoint",
      "location": ["path/to/file:line", "METHOD /route"],
      "actors": ["user"],
      "exposure": "authenticated internet-facing endpoint",
      "security_invariant": "what must always be true",
      "evidence": "concise redacted evidence",
      "impact": "concrete technical/business impact",
      "root_cause": "why the control failed",
      "remediation": "implemented or required root-cause fix",
      "regression_test": "test file/case or NOT_RUN with reason",
      "retest": "PASS/FAIL/NOT_RUN plus concise result",
      "standards": ["optional ASVS/API/CWE mapping"],
      "notes": "optional"
    }
  ],
  "residual_risks": [],
  "tooling": [
    {
      "name": "tool/command",
      "status": "RUN|NOT_RUN",
      "result": "concise result/reason"
    }
  ]
}
```

Do not add real secrets to any field.

## 9. Examples of correct disposition

### Scanner hit, protected path

A regex finds `dangerouslySetInnerHTML`, but the value is a compile-time constant. Record as candidate, inspect data flow, then mark `FALSE_POSITIVE` if no untrusted content can reach it.

### Broken object authorization

A route loads a record by request-supplied ID and checks only that the requester is authenticated. A unit/integration test shows User A can read User B's record. This is `CONFIRMED`; severity is usually High when the record is sensitive. Fix ownership/tenant authorization, add a negative regression test, retest, then mark `FIXED`.

### Dependency advisory not reachable

An audit tool reports a High advisory in an optional build-time dependency not shipped or invoked in production. Do not automatically report a High application vulnerability. Record the advisory review and explain reachability; upgrade safely if appropriate, but distinguish package severity from project exploitability.
