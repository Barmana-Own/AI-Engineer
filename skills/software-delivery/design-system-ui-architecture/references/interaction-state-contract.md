# Interaction and State Contract

## Table of contents

1. State categories
2. Loading
3. Empty states
4. Errors
5. Permissions and session state
6. Offline/degraded behavior
7. Success and acknowledgement
8. Destructive actions
9. Concurrency and stale data
10. Recovery principles

## 1. State categories

For each high-impact screen, explicitly evaluate whether these states apply:

- loading_initial;
- loading_incremental;
- empty_first_use;
- empty_no_results;
- success_content;
- validation_error;
- request_error;
- integration_error;
- partial_data;
- stale_data;
- permission_denied;
- session_expired;
- offline_or_degraded;
- destructive_confirmation;
- action_in_progress;
- action_success;
- action_failure;
- conflict_concurrent_update.

Mark non-applicable states as N/A with a reason for critical workflows rather than silently ignoring them.

## 2. Loading

Choose loading treatment based on expected wait and layout stability:

- preserve known content during background refresh when safe;
- use skeletons only when they reduce layout uncertainty;
- use progress indicators for indeterminate actions;
- use determinate progress when reliable progress data exists;
- prevent duplicate submit/action while the same mutation is pending;
- keep cancellation available for long-running cancellable tasks.

Do not block the whole interface for a local background operation unless necessary.

## 3. Empty states

Distinguish:

- true first-use/no-data state;
- no-results after search/filter;
- data hidden by permissions;
- data unavailable because integration failed.

Each state should explain the condition and provide the most useful safe next action when one exists.

## 4. Errors

Error contracts should define:

- what failed;
- whether user input was preserved;
- whether retry is safe;
- whether correction is needed;
- whether the error is local, page-level, or system-level;
- whether support/reference identifiers should be shown;
- how repeated failure escalates.

Avoid destructive reset after a recoverable error.

## 5. Permissions and session state

Permission denied should distinguish unavailable capability from missing resource when product/security policy requires it. Avoid exposing sensitive resource existence through UI copy when Stage 01 security/privacy constraints prohibit it.

For session expiry, specify the UX expectation for preserving safe unsaved work and returning the user to context after re-authentication where feasible. Stage 02 does not implement session handling.

## 6. Offline/degraded behavior

Only design offline behavior when product/device/network context makes it relevant. Define:

- read-only cached view versus unavailable view;
- queued action expectation only if later architecture can support it;
- stale-data indication;
- reconnect/retry behavior;
- unsafe actions that must be disabled.

Do not imply offline persistence exists unless it is a confirmed product/technical capability.

## 7. Success and acknowledgement

Use the least disruptive confirmation that still communicates completion:

- inline state change for obvious local updates;
- toast/status for background or cross-page actions;
- confirmation screen for major transactional completion;
- receipt/reference details when business flow requires them.

Do not show redundant success modals after every trivial action.

## 8. Destructive actions

Classify actions as:

- reversible;
- recoverable with admin/support;
- irreversible.

Use stronger confirmation as irreversibility and impact increase. Confirmation must name the object/action and consequence. Avoid generic "Are you sure?" for material operations.

## 9. Concurrency and stale data

When collaborative or approval workflows can conflict, define UX for:

- resource changed since load;
- action no longer valid;
- stale form submission;
- lock/ownership indication when relevant;
- refresh/reconcile path.

Do not silently overwrite user-visible concurrent changes when product risk is material.

## 10. Recovery principles

Prefer recovery in this order:

1. preserve user work;
2. explain the condition;
3. offer a safe retry/correction path;
4. offer alternate navigation or support path when needed;
5. surface technical detail only when useful to the user or support workflow.
