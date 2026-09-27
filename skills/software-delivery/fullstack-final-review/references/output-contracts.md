# Final Output Contracts

## Contents

- `docs/12-final-review.md`
- `release-manifest.json`
- User-facing completion response
- Archive integrity note

## `docs/12-final-review.md`

Use this structure unless the project requires additional sections:

1. **Executive release verdict**
   - PASS / FAIL;
   - production-ready qualifier;
   - blocking reason if FAIL.
2. **Review scope and environment**
   - project root/revision when available;
   - environment classification;
   - major tools/services available/unavailable.
3. **Stage 11 precondition**
   - evidence source and result.
4. **Product/requirement traceability summary**
   - total/core counts;
   - VERIFIED/PARTIAL/MISSING/BROKEN/EXCLUDED counts;
   - critical journey summary.
5. **Validation matrix**
   - G00–G19;
   - status;
   - evidence/check IDs;
   - concise reason.
6. **Security status**
   - open/closed findings by severity;
   - dependency/audit status;
   - key negative paths tested.
7. **Database/migration status**
8. **Build/test/runtime status**
9. **Production/operations readiness**
10. **Cross-stage repairs performed**
    - finding;
    - files changed;
    - gates invalidated;
    - rerun evidence.
11. **Known non-blocking issues**
    - owner/impact/workaround when applicable.
12. **NOT_RUN checks**
    - exact reason and release impact.
13. **How to run the project**
    - install;
    - env;
    - migrate;
    - build;
    - test;
    - start;
    - smoke.
14. **Artifact inventory**
15. **Final decision and completion markers**

Do not hide failures in an appendix.

## `release-manifest.json`

Follow `release-manifest.schema.json`. Include at minimum:

```json
{
  "schema_version": 1,
  "project": {
    "name": "...",
    "version": "...",
    "revision": "..."
  },
  "final_stage": {
    "id": 12,
    "status": "PASS"
  },
  "runtime": {},
  "components": [],
  "commands": {
    "install": [],
    "build": [],
    "test": [],
    "migrate": [],
    "start": []
  },
  "validation": {
    "gates": {},
    "evidence_summary": {},
    "traceability_summary": {},
    "security_summary": {}
  },
  "known_non_blocking_issues": [],
  "artifacts": [],
  "package": {
    "path": null,
    "sha256": null,
    "size_bytes": null,
    "integrity_record": ".final-review/package-result.json"
  }
}
```

Only include a timestamp when a reliable runtime clock is available. Do not fabricate version/revision.

## User-facing completion response

Keep it concise relative to the detailed report. State:
- verdict;
- major repairs/checks;
- unresolved non-blocking items;
- artifact/package paths;
- exact completion markers.

If FAIL, state the blocker and owning stage clearly rather than presenting a partial success as completion.

## Archive integrity note

When `release-manifest.json` is itself inside the release archive, do not attempt to store that archive's final SHA-256 inside the same manifest. The hash would change when the manifest changes. Store the final archive hash in `.final-review/package-result.json` and surface it in the handoff response. The manifest may point to that external audit record.
