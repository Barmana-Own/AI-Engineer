# Frontend Implementation Standards

## 1. Architectural boundaries

Use dependency direction intentionally.

Recommended conceptual direction:

`routes -> features -> shared UI/domain services -> low-level utilities`

Shared layers must not depend on feature-specific pages. Domain/API types may be shared when they represent real contracts rather than route-specific view models.

Avoid both extremes:

- one giant `components/` directory with no ownership;
- excessive micro-folders/interfaces created for theoretical future reuse.

Use the current framework's idioms unless they conflict with project requirements.

## 2. Routing

For every route, define:

- path and parameters;
- owning layout;
- actor/role visibility;
- data dependencies;
- loading/error/not-found behavior;
- page title/metadata when applicable;
- back/deep-link behavior;
- lazy boundary when appropriate.

Do not encode authorization as routing secrecy. A forbidden page should present appropriate UX, but the backend must remain authoritative later.

## 3. Design system

Prefer semantic tokens over raw palette/spacing values in feature code.

Separate:

- foundation tokens: spacing, typography, radius, elevation;
- semantic tokens: surface, text, border, primary action, destructive action, success/warning/error/info;
- component variants: size, emphasis, intent, state.

Components must handle at least the states they can actually reach: default, hover where relevant, focus-visible, disabled, pending/loading, invalid/error, selected/expanded where relevant.

Avoid page-specific overrides that mutate primitives unpredictably across the app.

## 4. Responsive behavior

Implement responsive behavior from content and workflow needs rather than device-brand assumptions.

Check:

- navigation collapse/expansion;
- sidebars/drawers;
- grids and cards;
- form grouping;
- tables/data grids;
- dialogs/sheets;
- charts/media;
- long text and localization expansion;
- touch target usability;
- sticky headers/footers;
- viewport height behavior on mobile browsers.

Do not solve overflow by globally applying `overflow-x: hidden` when content is actually broken.

## 5. RTL and localization

Use locale-driven direction at a stable root boundary.

Prefer logical properties and direction-aware layout primitives. Avoid manual `left/right` overrides unless the visual concept is physically directional rather than linguistically directional.

Mixed-direction content:

- emails, URLs, code, identifiers, tracking/reference numbers often need LTR isolation inside RTL UI;
- Persian/Arabic text must remain RTL;
- numbers/dates should follow the project's locale policy rather than arbitrary formatting;
- icons that represent direction/navigation may need mirroring; universal symbols generally should not be mirrored blindly.

Do not concatenate translated sentences from fragments when grammar/order may differ by locale.

## 6. Data/API transport

Keep one explicit transport boundary.

Transport responsibilities can include:

- base URL selection;
- request headers;
- credentials/cookies policy;
- request cancellation/timeout strategy;
- serialization/deserialization;
- normalized success/error envelopes;
- trace/request IDs if supplied;
- safe logging hooks.

Feature API modules should expose domain operations, not raw fetch calls scattered through components.

Retries:

- do not retry non-idempotent mutations automatically unless the contract explicitly supports it;
- avoid retry storms on authorization/validation failures;
- make retry UI explicit for recoverable reads.

## 7. State management

Classify state before choosing storage:

- ephemeral UI state -> component/local state;
- URL-addressable state -> router/search params where useful;
- server state -> query/cache layer;
- form state -> form library/local reducer as appropriate;
- cross-cutting client state -> global store/context only when multiple distant areas require it.

Avoid storing derived values when they can be computed reliably. Avoid duplicating the same server entity in multiple stores without synchronization rules.

## 8. Forms and validation

A robust form provides:

- typed values;
- deterministic validation rules;
- accessible labels/descriptions;
- field-level and form-level error handling;
- pending state;
- duplicate-submit protection;
- stable mapping for server validation errors;
- safe preservation of user input after recoverable failure;
- success/next-step feedback;
- upload validation UX when applicable.

Never hide server errors behind a generic success state.

## 9. Loading, empty, partial, and error states

Loading:

- preserve layout stability where practical;
- avoid indefinite spinners without context for long actions;
- distinguish initial page load from background refresh where UX benefits.

Empty:

- explain why there is no content when meaningful;
- provide next action when one exists;
- distinguish "no records" from "filters returned no matches" when applicable.

Partial:

- do not fail the entire page if one non-critical widget fails and the rest can remain usable;
- surface stale/partial data intentionally when the product permits it.

Error:

- normalize user-facing messages;
- offer retry for recoverable reads;
- preserve form data on recoverable mutation failure;
- do not expose stack traces, raw SQL/server internals, tokens, or sensitive payloads.

## 10. Accessibility

Use semantic HTML first. Add ARIA only where semantics require augmentation.

Required principles:

- one coherent heading hierarchy;
- landmarks for major page regions;
- programmatic labels for form controls;
- explicit accessible names for icon-only controls;
- keyboard operation for every interactive control;
- visible focus indication;
- sensible focus movement after route/modal/error changes;
- correct button vs link semantics;
- accessible table headers/captions when data tables are used;
- announced dynamic status where necessary;
- no essential information conveyed by color alone;
- reduced motion for non-essential animation.

For complex custom widgets, prefer a proven accessible primitive/library already approved in the project rather than reimplementing ARIA behavior from scratch.

## 11. Frontend security hygiene

### Untrusted HTML

Avoid raw HTML rendering. When product requirements truly require it, use an established sanitization strategy compatible with the framework and document the trust boundary.

### Untrusted URLs and redirects

Validate protocol/origin/path rules before navigation. Do not redirect to arbitrary user-supplied absolute URLs from query parameters.

### Secrets

Assume browser-delivered environment variables are public. Never place server secrets, private API keys, signing secrets, database credentials, or long-lived privileged tokens in client bundles.

### Authentication material

Follow the approved architecture. Do not log tokens. Do not introduce long-lived token persistence casually. If backend cookie/session design is pending, expose an auth client interface and document the required server contract instead of inventing insecure persistence.

### Logging

Log only what is needed for diagnosis. Redact tokens, credentials, sensitive user data, and full confidential payloads. Production logging hooks must fail safely.

### Authorization

Role-based rendering and route guards improve UX but are never the authorization boundary. Record required server enforcement for later stages.

### Dependency hygiene

Prefer existing dependencies. Add new packages only with clear need, compatible licensing/policy where applicable, and version compatibility. Do not run broad auto-fix upgrades that can change unrelated behavior without review.

## 12. Error boundaries and resilience

Use error boundaries or framework-equivalent mechanisms at scopes that preserve unaffected application areas.

Avoid one global fallback that turns every recoverable feature error into a blank application.

Define:

- route-level unexpected error fallback;
- feature-level fallback for isolated high-risk widgets when justified;
- reset/retry behavior;
- reporting hook that redacts sensitive context.

## 13. Performance

Do not optimize blindly. First preserve architecture that makes performance measurable.

Inspect:

- bundle/chunk growth;
- duplicate dependencies;
- avoidable client-side hydration/work;
- unnecessary rerenders;
- oversized images/media;
- long list rendering;
- serial data waterfalls;
- expensive parsing/calculation on every render;
- excessive provider scope.

If Stage 01 defines measurable budgets, make them part of the mandatory gate. Otherwise report actual evidence and obvious risks without inventing pass/fail numbers.

## 14. Testing

Prioritize behavior and contracts.

Good targets:

- validation schemas;
- formatting/date/number utilities with business impact;
- permission-driven visibility behavior (while not treating it as security enforcement);
- critical form interactions;
- route resolution and layouts;
- loading/empty/error states;
- API error normalization;
- query invalidation after mutations;
- complex accessible widgets;
- critical user journey smoke/integration tests.

Avoid tests that merely duplicate implementation details or snapshots with no semantic assertions.

## 15. Production-readiness prohibitions

A Stage 03 PASS must not leave:

- production code reading fixture JSON as a hidden fallback;
- hard-coded success paths instead of real adapters/contracts;
- secrets in source or public config;
- critical buttons with no handler;
- required routes pointing to placeholders;
- required forms that cannot submit through an explicit adapter boundary;
- known type/build failures;
- known severe keyboard traps;
- known horizontal overflow that breaks critical workflows;
- critical errors swallowed silently;
- documentation claiming verification that did not occur.
