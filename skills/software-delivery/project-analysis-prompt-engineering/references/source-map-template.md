# Source Map Template

Create `docs/01-source-map.md` with this structure.

# Stage 01 Source Map — [Project Name]

## Authority Policy

State the source precedence used by Stage 01.

## Source Inventory

| Source ID | Source / Path | Type | Owner | Authority | Freshness | Covers | Limitations |
|---|---|---|---|---|---|---|---|
| SRC-001 | ... | USER_BRIEF | User | PRIMARY | YYYY-MM-DD / unknown | ... | ... |

Allowed practical source types include `USER_BRIEF`, `USER_MESSAGE`, `PROJECT_FILE`, `CONTRACT`, `SPECIFICATION`, `REPOSITORY_DOC`, `API_DOC`, `EXTERNAL_OFFICIAL`, and `EXISTING_STAGE_ARTIFACT`.

Use authority values:
- `PRIMARY`
- `ACCEPTED_INTERNAL`
- `AUTHORITATIVE_EXTERNAL`
- `SECONDARY`
- `ASSUMPTION_ONLY`

## Explicit Constraints Extracted

List material constraints with source IDs.

## Known Gaps

List missing information that affects analysis. Distinguish ordinary ambiguity from a true blocker.

## Source Conflicts

Reference CONFLICT-* records. If none, state `None identified`.

## Research Triggers

List external facts requiring current verification, or state `None`.
