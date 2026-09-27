# Stage 08 Security Quality Gate

## Purpose

This gate decides whether the project may proceed to Stage 09. It is intentionally stricter than "security review completed."

## Mandatory PASS conditions

All of the following must be true:

1. Stage 07 was PASS and prior-stage artifacts were reviewed.
2. Scope and authorization are documented; unauthorized external testing was not performed.
3. Repository baseline and pre-existing user changes were captured where Git is available.
4. Architecture/attack surface and threat model cover all material roles, entry points, trust boundaries, sensitive assets and high-risk flows.
5. Every mandatory security domain is `VERIFIED`, has a documented finding, or is `N/A` with a concrete reason.
6. Authentication/session/recovery controls were reviewed when the application has user/service identity.
7. Object/property/function/role/tenant authorization was reviewed and negative boundary tests exist for material protected paths when testable.
8. No known unremediated Critical or High issue remains within project control.
9. Confirmed Critical/High fixes have targeted regression tests and successful retest evidence.
10. Medium findings were fixed when safe/proportionate or are documented as bounded residual risk with compensating controls and follow-up.
11. Injection, browser/output, CSRF/CORS, SSRF, file/path/parser and unsafe integration risks were assessed where applicable.
12. Secret/configuration review found no known live secret intentionally left in source/frontend/log output; any discovered live secret has a rotation recommendation and is redacted from artifacts.
13. Dependency/supply-chain review was performed using available tooling and reachability/context analysis. Tool absence is explicitly `NOT_RUN`, not silently ignored.
14. Runtime/container/deployment configuration was reviewed for production-safe defaults where relevant.
15. Security-relevant logging/error behavior was reviewed for both audit value and leakage.
16. Relevant unit/integration/security tests pass after fixes.
17. Relevant lint/typecheck/build checks pass when available, or failures are proved pre-existing and unrelated; a Stage 08 change must not leave the project newly broken.
18. Final diff review found no accidental unrelated edits, temporary bypasses, debug code or test secrets.
19. `docs/08-security-review.md` exists and accurately reflects final repository state.
20. `docs/security/08-security-findings.json` exists and is internally consistent.
21. `project-state.json` is updated without destroying unknown/prior data.
22. `scripts/validate_security_artifacts.py` passes when it can be run.

## FAIL conditions

Return FAIL and do not proceed when any of the following remains:

- a known Critical or High issue within project control is open, residual, or not successfully retested;
- a material authorization/tenant boundary is still broken;
- a Stage 08 fix introduced an unresolved regression;
- evidence is too weak to justify a claimed fix of a material issue;
- required security artifacts contradict code/test reality;
- required security regression coverage for a material fixed issue is absent without a genuine external blocker.

## BLOCKED conditions

Use BLOCKED only for a genuine external dependency that prevents a mandatory decision, such as unavailable authorized-environment credentials, required private API contract, or required external approval. Record:

- blocker owner if known;
- exact missing input/dependency;
- affected verification/finding;
- work already completed;
- exact condition that will unblock the stage.

A hard engineering problem is not a blocker.

## Residual Medium decision

Before allowing PASS with a Medium residual risk, verify all of these:

- severity is genuinely Medium, not a downgraded High;
- exploit path is bounded and documented;
- compensating controls currently reduce practical risk;
- there is no cheap safe fix being deferred without reason;
- follow-up action is concrete;
- Stage 09 knows what behavior to test.

## Final marker rules

Emit markers only after the gate decision and artifact validation.

PASS:

```text
STAGE_08_STATUS: PASS
SECURITY_GATE: CLEARED
NEXT_STAGE: 09-software-testing
```

FAIL:

```text
STAGE_08_STATUS: FAIL
SECURITY_GATE: NOT_CLEARED
NEXT_STAGE: NONE
```

BLOCKED:

```text
STAGE_08_STATUS: BLOCKED
SECURITY_GATE: NOT_CLEARED
NEXT_STAGE: NONE
```
