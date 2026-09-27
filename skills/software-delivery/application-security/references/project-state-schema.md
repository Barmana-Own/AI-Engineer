# project-state.json Stage 08 Update Contract

## Purpose

Preserve the master workflow state while adding an auditable Stage 08 result. Existing project schemas may contain additional keys; never delete or rename unknown keys.

## Preferred stage entry

Use stage ID `08-application-security`.

A preferred entry is:

```json
{
  "id": "08-application-security",
  "status": "PASS",
  "completed_at": "2026-09-15T12:00:00Z",
  "artifacts": [
    "docs/08-security-review.md",
    "docs/security/08-security-findings.json"
  ],
  "material_decisions": [
    "Centralized object ownership authorization for protected resource routes"
  ],
  "assumptions": [
    "Public production host was not actively tested; local/test evidence used"
  ],
  "risks": [],
  "next_stage": "09-software-testing"
}
```

For FAIL/BLOCKED set `next_stage` to `NONE` and explain unresolved findings/blockers in `risks`.

## `completed_stages` compatibility

If `completed_stages` is a list:

- replace the existing object whose `id` is `08-application-security`;
- otherwise append the new entry;
- preserve order of unrelated entries.

If `completed_stages` is a dictionary/map:

- set key `08-application-security` to the stage entry;
- preserve all unrelated keys.

If the existing field has an unexpected scalar/string shape, do not overwrite it automatically. Update manually according to the project's established schema or leave the stage BLOCKED only if state preservation truly cannot be resolved.

## Optional top-level fields

If the existing project schema already uses top-level `current_stage`, `next_stage`, `status`, `risks`, or `updated_at`, update them consistently with prior conventions. Do not invent parallel fields when the project already has an established structure.

## Status semantics

- `PASS`: security gate cleared; next stage `09-software-testing`.
- `FAIL`: technical/security quality gate not cleared; next stage `NONE`.
- `BLOCKED`: external dependency prevents mandatory completion; next stage `NONE`.

A Stage 08 report existing on disk does not imply PASS.

## Update discipline

Before writing:

1. parse the existing JSON;
2. preserve unknown keys exactly where possible;
3. replace only the Stage 08 entry and established workflow pointers;
4. write atomically through a temporary file/rename;
5. re-parse the final file;
6. ensure the gate status matches the report/findings ledger.

Use `scripts/update_project_state.py` when the existing shape is compatible. The script refuses destructive/unknown `completed_stages` shapes rather than guessing.
