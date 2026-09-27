# Conditional Domain Lenses

## Table of Contents

1. Usage rule
2. Workflow and approval systems
3. Marketplace and multi-party systems
4. Commerce and payment systems
5. Logistics and field operations
6. Legal, government, and regulated workflows
7. AI and LLM-enabled systems
8. SaaS and multi-tenant products
9. Content, community, and moderation products
10. File/document-heavy systems
11. Realtime and notification-heavy systems
12. Device, kiosk, and hardware-integrated systems

## 1. Usage rule

Apply only lenses materially relevant to the project. These are omission-detection checklists, not feature catalogs. Never add a capability to scope merely because it appears below.

For each applicable lens, inspect the listed concerns and either:
- map them to existing requirements/rules/risks;
- create a justified requirement/risk/question;
- or mark the concern not applicable in the readiness review when its absence could otherwise look accidental.

## 2. Workflow and approval systems

Check:
- draft vs submitted state;
- validation before submission;
- assignment/ownership;
- reviewer/approver separation;
- request-for-change/rejection reason;
- resubmission;
- reassignment;
- escalation;
- cancellation/closure/reopen;
- history/audit trail;
- SLA/timing only if supplied or explicitly assumed;
- concurrent edits or stale decisions where material.

## 3. Marketplace and multi-party systems

Check:
- actor sides and role separation;
- listing/service lifecycle;
- discovery/search/matching only if requested;
- offer/quote/order lifecycle;
- acceptance/rejection/cancellation;
- platform moderation or dispute role when relevant;
- fees/commission only if supplied;
- ratings/reviews only if requested;
- identity/trust concerns;
- cross-party data visibility;
- dispute/refund/escalation when money or fulfillment is involved.

## 4. Commerce and payment systems

Check:
- cart/order/payment state distinctions;
- payment initiation/result verification;
- duplicate payment/idempotency concerns;
- failed/pending/expired payment;
- refund/reversal/cancellation when applicable;
- amount/currency/tax/fee source of truth;
- payment provider callback/webhook trust;
- reconciliation/audit needs;
- receipt/invoice requirements only when requested or legally confirmed;
- sensitive payment data boundaries.

## 5. Logistics and field operations

Check:
- shipment/task/job lifecycle;
- origin/destination or service location;
- assignment/dispatch;
- driver/operator/vehicle/equipment roles when relevant;
- status/event timeline;
- proof of pickup/delivery/service;
- exception/delay/damage/cancellation;
- geolocation privacy and freshness;
- offline/poor-connectivity behavior;
- external mapping/telematics/customs/transport integrations when applicable;
- handoff of custody or responsibility.

## 6. Legal, government, and regulated workflows

Check:
- authoritative regulation/process source;
- jurisdiction/version/effective date;
- identity/representation/authority;
- evidentiary documents;
- auditability/non-repudiation intent when material;
- legal status transitions;
- retention/deletion constraints only when confirmed;
- appeals/objections/corrections;
- human approval responsibilities;
- accessibility/language obligations when confirmed;
- strict separation between legal fact and professional assumption.

## 7. AI and LLM-enabled systems

Check:
- user-visible AI capability and its exact role;
- model/provider dependency;
- input/output data sensitivity;
- prompt/content retention assumptions;
- hallucination/error impact;
- human review requirements for high-impact outputs;
- evaluation criteria and failure behavior;
- fallback/degraded behavior;
- prompt injection/data exfiltration exposure when external content is processed;
- explainability/audit needs when decisions matter;
- cost/rate/latency dependency only when material.

## 8. SaaS and multi-tenant products

Check:
- tenant/account/workspace concept;
- user membership lifecycle;
- tenant isolation intent;
- organization-level roles;
- invitation/removal/deactivation;
- ownership transfer if relevant;
- configuration scope: global vs tenant vs user;
- subscription/billing only if requested;
- tenant-level audit/export/delete requirements when applicable.

## 9. Content, community, and moderation products

Check:
- content lifecycle;
- author ownership/edit/delete;
- visibility/audience rules;
- moderation/reporting only if relevant;
- blocked/restricted users;
- comments/reactions only if requested;
- abuse/spam/rate concerns;
- copyright/consent questions when material;
- search/indexing visibility implications.

## 10. File/document-heavy systems

Check:
- allowed document purpose and ownership;
- upload/download/preview requirements;
- file size/type constraints only when supplied or safely assumed;
- version/replacement history;
- validation/scanning requirements at requirement level;
- access visibility;
- retention/archive/delete questions;
- evidence hash/signature requirements only when requested or justified;
- failed/interrupted upload handling when material.

## 11. Realtime and notification-heavy systems

Check:
- which event requires notification;
- channel and recipient intent;
- delivery vs read semantics when relevant;
- duplicate notification behavior;
- user preference/opt-out constraints;
- retry/failure behavior;
- ordering/freshness for realtime data;
- degraded behavior when realtime transport fails;
- latency targets only when supplied or assumed explicitly.

## 12. Device, kiosk, and hardware-integrated systems

Check:
- device identity/registration;
- online/offline behavior;
- peripheral/camera/scanner/sensor dependency;
- permission/OS/platform constraints;
- local data sensitivity;
- reconnect/synchronization;
- firmware/client version compatibility when relevant;
- physical tampering or operator misuse risks;
- operational fallback when hardware is unavailable.
