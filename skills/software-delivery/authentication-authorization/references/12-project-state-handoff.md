# Project State and Stage 08 Handoff

## Contents

- [Purpose](#purpose)
- [Preserve state](#preserve-state)
- [Minimum Stage 07 state](#minimum-stage-07-state)
- [Example logical record](#example-logical-record)
- [Documentation consistency check](#documentation-consistency-check)
- [Stage 08 handoff](#stage-08-handoff)
- [BLOCKED state](#blocked-state)
- [Final output consistency](#final-output-consistency)


## Purpose

Use this reference to update `project-state.json` without destroying upstream data and to provide a precise handoff to broader application-security work.

## Preserve state

- Read the existing file before writing.
- Preserve unknown top-level and nested keys.
- Preserve prior stage history.
- Do not reorder or reformat the entire file unnecessarily if the repository minimizes diffs.
- Follow the project's existing stage-record schema when one exists.
- If no schema exists, add Stage 07 information conservatively rather than replacing the file.

## Minimum Stage 07 state

Record, using the project's existing field naming when possible:

- stage id: `07` or `07-authentication-authorization`;
- status: `PASS` or `BLOCKED`;
- completion timestamp if the workflow stores timestamps;
- artifacts created/updated;
- implementation summary;
- material decisions;
- assumptions;
- auth mechanisms selected;
- identity types;
- authorization model;
- tenant/ownership model;
- MFA/step-up decision;
- tests/commands run and outcomes or references to evidence document;
- static-audit result path;
- residual risks;
- blockers if any;
- next stage on PASS: `08-application-security`;
- next stage on BLOCKED: none.

## Example logical record

Adapt field names to the existing state file; do not blindly copy this shape:

```json
{
  "stage": "07-authentication-authorization",
  "status": "PASS",
  "artifacts": [
    "docs/07-authentication-authorization.md",
    "docs/security/07-authorization-matrix.md",
    "docs/security/07-auth-test-evidence.md",
    "docs/security/07-auth-static-audit.json"
  ],
  "decisions": [],
  "assumptions": [],
  "residual_risks": [],
  "next_stage": "08-application-security"
}
```

The example is semantic guidance, not a replacement schema.

## Documentation consistency check

Before writing PASS:

- every artifact path in state exists;
- test evidence references real commands/tests;
- stage document describes the mechanism actually implemented;
- authorization matrix uses routes/actions that exist;
- residual risks are not hard blockers disguised as accepted risk;
- next stage is correct;
- no secret/token is copied into state.

## Stage 08 handoff

Create a concise handoff section in `docs/07-authentication-authorization.md` covering only unresolved or next-stage-relevant items.

Include:

### Security boundaries established

- auth entrypoints;
- session/token mechanism;
- main authorization enforcement points;
- tenant scoping approach;
- high-risk/step-up controls;
- auth audit/logging locations.

### Stage 08 areas to inspect

Record broader issues discovered but not owned by Stage 07, such as:

- input/injection risks;
- XSS/CSP;
- SSRF;
- file upload/content handling;
- unsafe deserialization;
- security headers;
- general CORS posture beyond auth-specific impact;
- dependency vulnerabilities;
- secret-management posture outside auth credentials;
- supply chain/build pipeline;
- insecure temporary files;
- broad logging/privacy concerns;
- encryption/key management outside auth scope;
- denial-of-service/resource controls outside auth endpoints.

Do not mark these fixed unless Stage 07 actually fixed and verified them.

### Auth-specific watch items for Stage 08

Provide:

- endpoints deserving dynamic security testing;
- auth middleware/policy modules to protect during refactors;
- known third-party auth dependencies;
- accepted residual auth risks;
- environment/provider verification still needed if non-blocking under the project policy;
- test suites that Stage 08 must keep green.

## BLOCKED state

When blocked:

- do not list Stage 07 under a completed/passed collection if the state model distinguishes completion from attempted stages;
- record blocker and completed partial work;
- keep next stage empty/none;
- preserve artifacts/tests produced so far;
- never fabricate PASS to keep orchestration moving.

## Final output consistency

The chat completion marker, project-state status, and evidence-document gate status must agree.

Allowed final combinations:

- state PASS + evidence PASS + `STAGE_07_STATUS: PASS`;
- state BLOCKED + evidence contains BLOCKED/FAIL requirement + `STAGE_07_STATUS: BLOCKED`.

Any mismatch is itself a stage defect and must be corrected before handoff.
