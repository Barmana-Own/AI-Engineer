# Functional and Exploratory QA

## Table of contents

1. Mission
2. Happy-path verification
3. Forms and validation
4. Navigation and lifecycle behavior
5. State-machine testing
6. Duplicate and idempotency behavior
7. Failure and recovery testing
8. Concurrency and stale-state testing
9. File and media workflows
10. Search/filter/sort/pagination
11. Notifications and asynchronous behavior
12. Time, locale, and formatting
13. Exploratory charters
14. Exit criteria

## 1. Mission

Functional QA proves that business behavior works from the user's perspective and that system state matches what the UI claims. Exploratory QA deliberately targets assumptions, transitions, and recovery paths not fully represented in automated tests.

## 2. Happy-path verification

For each release-critical journey:

- begin from a known state;
- use a realistic role and realistic data;
- execute the complete flow rather than jumping directly to the final endpoint;
- confirm loading/progress state does not allow accidental repeated mutation;
- confirm success feedback is accurate;
- confirm persisted state after refresh/re-login;
- confirm downstream visibility to other roles;
- confirm expected events/notifications/jobs when required.

If a success toast appears but persistence fails, classify the journey as failed.

## 3. Forms and validation

For each critical form test:

### Required fields

- missing one required field;
- missing all required fields;
- field becomes invalid after a dependent choice changes;
- server validates requiredness even if client checks are bypassed.

### Length and shape

- shortest valid;
- longest valid;
- just outside valid bounds;
- whitespace-only;
- leading/trailing whitespace;
- multiline content;
- long unbroken strings;
- Unicode and Persian/Arabic characters where relevant;
- mixed RTL/LTR text where relevant.

### Cross-field rules

- mutually exclusive values;
- dependent selections;
- date ranges;
- totals/percentages;
- start/end ordering;
- conditional required fields.

### Error behavior

- field error points to the correct field;
- focus moves appropriately for blocked submission;
- user input is preserved when safe;
- server errors are not shown as false success;
- technical stack traces are not exposed to normal users.

## 4. Navigation and lifecycle behavior

Check critical flows under:

- browser Back;
- browser Forward;
- refresh/reload;
- hard reload;
- opening in a new tab if supported;
- navigating away mid-edit;
- returning after session expiration;
- deep-linking directly to protected routes;
- reopening a completed/pending record from history.

Look for duplicate submission, stale UI, lost draft state, impossible navigation, or unauthorized access after history navigation.

## 5. State-machine testing

For each entity with lifecycle states:

1. list valid transitions;
2. list invalid transitions;
3. test transition by every allowed role;
4. attempt transition by a forbidden role;
5. repeat the same transition;
6. attempt old/stale transition after another actor changes state;
7. verify side effects and timestamps;
8. verify UI labels/actions match canonical backend state.

Do not allow the UI and server to disagree silently about current state.

## 6. Duplicate and idempotency behavior

For material mutations test as applicable:

- double click;
- rapid repeated submit;
- retry after network timeout;
- client resend after ambiguous response;
- webhook replay;
- queue redelivery;
- refresh after POST/submit;
- duplicate payment/order/request token if domain supports it.

Expected result is either explicit idempotency or a safe, deterministic rejection. Duplicate records or duplicate side effects are defects unless requirements specify otherwise.

## 7. Failure and recovery testing

Inject or simulate failures safely:

- backend 4xx;
- backend 5xx;
- timeout;
- slow response;
- dropped network after mutation request;
- unavailable downstream integration;
- queue/job failure;
- upload failure;
- stale CSRF/session token if relevant.

Verify:

- no false success;
- no inconsistent partial state;
- user receives actionable feedback;
- retry behavior is safe;
- progress indicators terminate;
- irreversible operations are not repeated accidentally;
- logs contain enough context without secrets.

## 8. Concurrency and stale-state testing

Use for records that multiple actors can edit/approve/process.

Scenarios:

- two users open same record, one saves first;
- two approvals occur nearly simultaneously;
- one actor changes status while another submits old form;
- same account uses two tabs;
- repeated API mutations arrive concurrently.

Verify optimistic/pessimistic locking or domain conflict handling behaves safely. Silent last-write-wins is a defect when it can lose important user or business data.

## 9. File and media workflows

Check:

- valid upload;
- multiple uploads where supported;
- exact size/type boundaries;
- extension/MIME mismatch;
- unsupported type;
- zero-byte/corrupt file;
- duplicate filename;
- unsafe filename characters;
- preview/download behavior;
- replace/remove behavior;
- authorization to access uploaded content;
- failed upload cleanup;
- object storage/database consistency.

Do not execute malicious payloads; use benign test artifacts to verify controls.

## 10. Search/filter/sort/pagination

Check:

- empty query;
- no results;
- exact match;
- partial match;
- case/locale behavior if specified;
- multiple filters combined;
- clearing filters;
- sorting null and equal values;
- pagination boundaries;
- filter persistence across pagination;
- deleted/changed records during paging;
- unauthorized records never appearing.

## 11. Notifications and asynchronous behavior

For email/SMS/push/webhooks/jobs:

- trigger once;
- verify payload/recipient/template when inspectable;
- verify duplicate suppression;
- verify failure/retry policy;
- verify sensitive data is not overexposed;
- verify job completion changes state only when intended;
- verify UI handles eventual consistency honestly.

If delivery provider is mocked, say so explicitly.

## 12. Time, locale, and formatting

Where relevant test:

- timezone conversion;
- midnight/day boundaries;
- DST if target locales use it;
- Jalali/Gregorian conversion when required;
- expired/expiring timestamps;
- server vs client timezone differences;
- decimal and currency formatting;
- localized digits if specified;
- RTL punctuation and mixed-direction identifiers.

## 13. Exploratory charters

Run short charters centered on risk rather than random clicking.

### Charter A - "What if I repeat it?"

Repeat create/update/pay/approve/upload actions under fast clicks, refreshes, retries, and duplicate network requests.

### Charter B - "What if I leave and return?"

Interrupt forms and workflows using navigation, refresh, logout/login, expired session, and second tab.

### Charter C - "What if I am the wrong user?"

Try direct URL/API/object access as another role or non-owner.

### Charter D - "What if the data is ugly?"

Use empty, long, Unicode, mixed-direction, boundary, duplicate, stale, and malformed data.

### Charter E - "What if a dependency fails?"

Exercise timeout, downstream error, queue failure, upload failure, or unavailable integration where safely controllable.

### Charter F - "What if two actors act at once?"

Exercise approval/edit/update races on high-value records.

Record charter scope, discoveries, defects, and coverage gaps.

## 14. Exit criteria

Functional/exploratory work is complete when:

- every release-critical journey has executed evidence;
- critical negative/recovery variants have been exercised;
- critical role and state boundaries have been tested;
- discovered P0/P1 defects are closed and reverified;
- residual P2/P3 findings are documented;
- untested critical behavior is explicitly blocked rather than omitted.
