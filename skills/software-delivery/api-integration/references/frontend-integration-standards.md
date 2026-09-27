# Frontend Integration Standards

## Contents
1. Goals
2. Client architecture
3. Configuration and secrets
4. Types and mapping
5. Query/request serialization
6. Request lifecycle and cancellation
7. Mutations and cache/state synchronization
8. Error-state UX
9. Upload/download integration
10. Mock removal
11. Integration checklist

## 1. Goals

The production frontend must consume the real backend through a predictable integration boundary. UI components should not need to understand low-level transport quirks or arbitrary provider error payloads.

Preserve the project's established state/query library if it is coherent.

## 2. Client architecture

Prefer a centralized client/service layer appropriate to the framework, such as:
- generated OpenAPI client;
- typed API module;
- repository/service abstraction;
- query/mutation hooks backed by a shared HTTP client.

Avoid scattering raw `fetch`, Axios instances, base URLs, headers, and error parsing across unrelated components.

A shared client should own, where relevant:
- base URL;
- default headers;
- serialization;
- response parsing;
- timeout/cancellation behavior;
- common error normalization;
- request/correlation propagation already used by the project.

Authentication injection may already exist; preserve it. Final auth lifecycle hardening belongs to Stage 07.

## 3. Configuration and secrets

API origins/base URLs must be environment-configurable according to framework conventions.

Frontend code may contain public configuration intended for browsers, but never embed server secrets, private API keys, signing secrets, database credentials, or privileged tokens.

Avoid a dangerous default where missing production config silently points to a mock server.

Validate required production configuration during build/startup when repository patterns support it.

## 4. Types and mapping

Prefer contract-derived/generated types when the project already uses code generation.

Otherwise maintain clear DTO types and map them to UI/domain view models where shapes differ.

Do not cast untrusted network data blindly to a TypeScript type and assume runtime validity when the project has runtime schema validation available and risk warrants it.

Map:
- server enums to stable UI states;
- date strings to deliberate date handling;
- decimal/money values without precision loss;
- nullable/optional values explicitly.

## 5. Query/request serialization

Use one stable serialization convention for:
- arrays;
- booleans;
- dates;
- nested filters;
- sort fields/direction;
- cursors/page values;
- empty/undefined values.

Do not send accidental UI-only fields or entire form state objects when the API expects a narrower DTO.

## 6. Request lifecycle and cancellation

For route changes, autocomplete, live search, filters, or rapidly repeated reads, prevent stale responses from overwriting newer state.

Use the framework/query library's cancellation/deduplication semantics or AbortController-equivalent behavior when useful.

Represent loading deliberately. Avoid full-screen loading for a small subquery unless product design requires it.

## 7. Mutations and cache/state synchronization

After successful mutation:
- update authoritative local/query cache safely; or
- invalidate/refetch affected resources; or
- navigate to the server-created resource using returned ID.

Do not leave the UI showing the old fixture or optimistic state indefinitely without reconciliation.

For optimistic updates, define rollback behavior on failure.

For retry-prone high-impact mutations, do not auto-retry blindly unless the API idempotency contract makes it safe.

## 8. Error-state UX

Map server failures by class:
- field validation -> field-level errors where possible;
- not found -> empty/removed/not-found state;
- conflict -> refresh/reconcile prompt or domain-specific state;
- dependency unavailable -> retryable service message when safe;
- unexpected error -> generic safe message and request ID when available.

Do not render raw stack traces or uncontrolled upstream messages.

Ensure failed requests do not silently look successful.

## 9. Upload/download integration

Uploads should use the real server contract and show applicable:
- client-side size/type pre-check as convenience only;
- progress when useful;
- server validation errors;
- cancellation/retry policy;
- successful file metadata/readback.

Client-side checks never replace server enforcement.

Downloads should use server-provided identifiers/URLs and not construct server filesystem paths.

## 10. Mock removal

Production integration is incomplete if production screens still source authoritative data from fixtures, static JSON, hard-coded arrays, or a fake service.

Audit:
- imports;
- environment switches;
- dependency injection defaults;
- localStorage seed logic;
- service worker/MSW production activation;
- build-time aliases;
- demo feature flags.

Keep mocks isolated to tests/dev/Storybook when production builds cannot select them.

## 11. Integration checklist

For every core frontend journey verify:
- real endpoint is called;
- request payload matches OpenAPI/handler;
- response is parsed/mapped correctly;
- loading state is visible/appropriate;
- empty state is correct;
- field errors map correctly;
- non-field error is handled;
- mutation updates/invalidation are correct;
- refresh/reload reflects persisted server truth;
- stale requests cannot corrupt visible state where race is plausible;
- no production fixture path remains.
