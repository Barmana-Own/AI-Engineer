# Stage 03 Contract

## 1. Entry conditions

Stage 03 may start only after examining Stage 01 and Stage 02 outputs. It may finish with PASS only when Stage 02 is confirmed PASS.

Artifact resolution priority:

1. Paths explicitly referenced by `project-state.json`.
2. Existing workflow manifest/orchestrator metadata.
3. Conventional files under `docs/`, especially names matching `01-*`, `02-*`, `requirements*`, `product*`, `ui*`, `ux*`, or `design*`.
4. Existing repository documentation clearly identified as the approved source.

Do not assume a missing conventional filename means the source does not exist. Search the repository before blocking.

## 2. Minimum Stage 01 information to recover

Recover enough information to identify:

- actors and roles;
- critical user journeys;
- functional requirements affecting UI;
- business rules that change screen behavior;
- NFRs affecting frontend architecture;
- security/privacy constraints relevant to the browser/client;
- localization/locale expectations;
- external integrations visible to the user;
- scope exclusions and assumptions.

## 3. Minimum Stage 02 information to recover

Recover enough information to identify:

- route/page/screen inventory;
- navigation hierarchy;
- layouts and responsive behavior;
- component/design-system direction;
- typography and design tokens if specified;
- loading, empty, validation, error, permission, and success states;
- interaction and motion behavior;
- RTL/LTR/localization rules;
- accessibility requirements;
- data displayed and actions triggered per screen;
- approved deviations or unresolved design decisions.

## 4. Stage 02 reconciliation rules

When Stage 02 and the current repository disagree:

- Prefer Stage 02 for product/UI intent.
- Prefer the repository for established technical conventions if they can realize Stage 02 without violating requirements.
- Do not discard a stable architecture solely to match superficial Stage 02 implementation suggestions.
- If Stage 02 conflicts with Stage 01 business rules, Stage 01 business intent wins unless Stage 02 records an approved change.
- If Stage 02 requires insecure behavior, implement the closest safe UX and document the correction.
- If Stage 02 requires an inaccessible interaction, preserve intent while correcting the accessibility defect.
- If a contradiction changes scope or business semantics and cannot be resolved from evidence, record it as a critical ambiguity and block only when implementation would otherwise be materially wrong.

## 5. Existing-repository modes

Classify the repository before editing.

### Mode A - Mature existing frontend

Preserve architecture. Fill coverage gaps, normalize inconsistent boundaries, repair defects, and extend tests. Avoid scaffolding a second frontend.

### Mode B - Partial/prototype frontend

Keep reusable work, remove or isolate prototype-only shortcuts, establish production boundaries, complete routes/states, and add verification.

### Mode C - Empty/new frontend area

Use the stack already approved by prior stages. If no stack is approved, choose a stable stack appropriate to routing/SSR/SEO/data needs and current repository ecosystem. Record why it fits the product and why a simpler option is insufficient.

### Mode D - Monorepo

Identify workspace manager and app package boundaries. Run commands from the correct package/workspace and avoid modifying sibling applications without direct relevance.

## 6. Allowed scope

Stage 03 may:

- create/modify frontend application files;
- create client-facing types and schemas;
- create API adapters/interfaces without implementing backend logic;
- create development/test fixtures in isolated adapters;
- create frontend tests;
- add narrowly necessary frontend dependencies compatible with the current stack;
- update frontend documentation and environment examples without secrets;
- define requirements/handoff notes for backend/integration stages.

Stage 03 must not:

- implement server business rules as browser-only authority;
- add or change database schemas/migrations;
- implement backend authorization as if frontend guards were sufficient;
- fabricate backend endpoints or mark them operational;
- create deployment infrastructure unrelated to running/verifying the frontend;
- expose secrets in browser code;
- silently replace the project package manager or framework;
- perform broad dependency modernization unrelated to Stage 03.

## 7. Assumption policy

Use three classes:

- `ASSUMED_SAFE`: can be inferred without changing business meaning; continue and record.
- `DEFERRED_CONTRACT`: frontend can define an interface and continue while backend implementation waits for later stage; record exact contract need.
- `BLOCKING_EXTERNAL`: cannot implement or verify correctly without unavailable external/private information or a failed precondition.

Examples:

- Exact empty-state copy absent -> `ASSUMED_SAFE` if design tone is known.
- Backend endpoint not implemented yet -> `DEFERRED_CONTRACT`; create typed interface/adapter boundary.
- Stage 02 explicitly BLOCKED -> `BLOCKING_EXTERNAL` for Stage 03 completion.
- Private design system package required but inaccessible and no approved fallback exists -> potentially `BLOCKING_EXTERNAL`.

## 8. Blocker discipline

Before declaring BLOCKED:

1. Search existing project artifacts.
2. Inspect relevant configuration/source.
3. Attempt a safe fallback that preserves requirements.
4. Distinguish missing implementation work from external dependency.
5. Record what was attempted, exact missing evidence, and what unblocks the stage.

Ordinary compile errors, incomplete routes, missing tests, inconsistent components, or fixable layout defects are not blockers. They are Stage 03 work.
