# Requirement Traceability Contract

Traceability is mandatory for final release. The purpose is to prove that approved scope reached the implementation and that the implementation is verified.

## Required file

Maintain `.final-review/traceability.json` following `traceability.schema.json`, with this conceptual structure:

```json
{
  "requirements": [
    {
      "id": "REQ-001",
      "title": "...",
      "core": true,
      "approved_source": "docs/01-requirements.md",
      "status": "VERIFIED",
      "implementation": ["src/..."],
      "interfaces": ["POST /api/...", "/app/..."],
      "data": ["users", "migration:..."],
      "tests": ["tests/..."],
      "evidence": ["check-id-or-manual-evidence"],
      "notes": ""
    }
  ],
  "orphans": [],
  "summary": {}
}
```

## Allowed requirement statuses

- `VERIFIED` — implementation exists and appropriate verification is current.
- `IMPLEMENTED_UNVERIFIED` — implementation exists but required verification is missing; core requirements block PASS.
- `PARTIAL` — only part of the approved behavior exists; core requirements block PASS.
- `MISSING` — no valid implementation; core requirements block PASS.
- `BROKEN` — implementation exists but current evidence shows failure; blocks PASS.
- `EXCLUDED_APPROVED` — explicitly excluded/deferred by approved scope evidence; does not block.
- `NOT_APPLICABLE` — requirement is proven not applicable to the current release; reason required.

Do not use `VERIFIED` solely because a file with a plausible name exists.

## Traceability procedure

For every approved core requirement:
1. identify user/actor and expected observable outcome;
2. locate the production implementation path;
3. locate API/backend/business-rule enforcement where relevant;
4. locate persistence/data changes where relevant;
5. identify tests or runtime verification proving the behavior;
6. test negative conditions for security/business rules when risk warrants;
7. record status and evidence.

## Critical journey tracing

For each critical user journey, produce an end-to-end chain such as:

`UI route → component/form → API client → route/controller → authz → service/domain rule → repository/DB/integration → response → UI state`

Broken links are findings even if isolated unit tests pass.

## Orphan analysis

Record code/features that:
- have no approved requirement;
- are production-reachable experimental/debug features;
- duplicate another implementation;
- expose an undocumented endpoint/admin action;
- are old code paths still selectable by configuration.

Not every orphan blocks release. Production-reachable privileged/debug behavior usually requires security review.

## Coverage quality

Use verification proportional to risk:
- simple static text/display: source + targeted UI test may be enough;
- mutation/business rule: backend/integration test preferred;
- auth/authorization: negative-path runtime or strong integration tests required where possible;
- payment/legal/security-sensitive flow: stronger end-to-end and failure-mode evidence expected;
- database migration: executable migration evidence required.

## Final traceability blockers

PASS is prohibited when:
- any `core=true` requirement is `MISSING`, `BROKEN`, `PARTIAL`, or `IMPLEMENTED_UNVERIFIED`;
- a core requirement is marked excluded without approved evidence;
- a critical journey reaches a mock/fake/dev implementation in production configuration;
- the traceability file materially contradicts current source/test results.
