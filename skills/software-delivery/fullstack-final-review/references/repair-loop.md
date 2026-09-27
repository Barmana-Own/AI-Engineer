# Cross-Stage Repair Loop

The final stage is allowed to repair earlier-stage defects when the intended behavior is clear and repair is safe. Do not bounce trivial defects backward if they can be corrected and verified now.

## 1. Record before editing

Create a finding before changing code. Include root-cause hypothesis and owning stage.

Suggested ownership:
- Stage 01: misunderstood/missing approved requirement;
- UI/design stage: unusable journey/design contract issue;
- architecture stage: component boundary/topology contradiction;
- API/backend stage: contract/business logic issue;
- data stage: schema/migration issue;
- security stage: auth/security control defect;
- test/QA stage: missing/invalid regression coverage;
- deployment/ops stage: runtime/container/config/runbook issue.

Use the actual workflow's stage mapping if available.

## 2. Determine repair scope

Prefer the smallest coherent fix, not the smallest textual diff.

A coherent fix may require changing:
- implementation;
- test;
- API schema/client type;
- migration;
- documentation;
- configuration template.

Do not patch only one layer when doing so creates contract drift.

## 3. Preserve compatibility intentionally

Before changing public API/schema/DB behavior, identify consumers and migration compatibility. Avoid accidental breaking changes during final review.

If approved requirement is ambiguous and multiple incompatible behaviors are plausible, use the safest existing approved contract rather than inventing a new product decision.

## 4. Add regression proof

Where technically meaningful, add/update a test that would have failed before the repair.

For security findings, include a negative regression path.
For migration findings, include a fresh/upgrade migration check where feasible.
For API drift, update contract/client tests.

## 5. Invalidate evidence

Immediately mark affected gates stale/PENDING. Use dependency guidance from `gate-matrix.md`.

Do not reuse pre-fix build/test/security evidence to justify post-fix PASS.

## 6. Re-run in dependency order

Typical order after a code repair:
1. focused test reproducing the defect;
2. local static/type checks for changed module;
3. full required relevant suite;
4. integration/contract tests;
5. production build;
6. runtime/smoke if affected;
7. security/hygiene if affected.

## 7. Close finding only with proof

Set finding to CLOSED only when:
- root cause is addressed;
- relevant regression evidence passes;
- no new blocking regression exists;
- docs/contracts are updated where required.

`REPAIRED_PENDING_VERIFY` is still open for final-gate purposes.

## 8. Escalate true product decisions

Return to an earlier stage instead of guessing when repair requires:
- changing approved business policy;
- changing legal/compliance meaning;
- choosing between incompatible externally owned API contracts;
- credentials/authorization not available;
- destructive production action requiring approval.

Record the exact decision needed and why it blocks release.
