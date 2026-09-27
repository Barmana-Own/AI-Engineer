# AI, LLM, RAG, and Agent Security Review

## Table of contents

1. Trigger and scope
2. AI trust boundaries
3. Prompt injection and instruction hierarchy
4. Tool/action authorization
5. Sensitive data and provider egress
6. RAG and document isolation
7. Model output handling
8. Structured outputs and downstream sinks
9. Agent memory and cross-user isolation
10. Browsing, URL fetch and SSRF
11. Cost/resource abuse
12. Model/provider credentials
13. Human confirmation and high-impact actions
14. Logging and observability
15. Security regression tests

## 1. Trigger and scope

Use this playbook only when the project invokes an LLM/model, uses RAG/vector retrieval, exposes AI-generated content, or gives a model tools/actions. Treat model behavior as probabilistic and untrusted. A model prompt is not an authorization boundary.

Identify:

- model/provider and SDK;
- prompts/system instructions;
- user-controlled prompt/context;
- retrieved documents/data sources;
- tools/functions/actions;
- memory/conversation storage;
- model output sinks;
- external browsing/fetching;
- sensitive data sent to providers;
- cost-bearing endpoints.

## 2. AI trust boundaries

Record boundaries such as:

- user -> prompt;
- retrieved document -> model context;
- model output -> application renderer;
- model output -> tool arguments;
- tool result -> model context;
- model/provider -> application;
- one tenant's memory/vector data -> another request.

Treat user content, retrieved documents, web pages, tool results and model output as untrusted unless separately verified.

## 3. Prompt injection and instruction hierarchy

Do not attempt to solve prompt injection solely by adding stronger prose such as "ignore malicious instructions." Design the application so untrusted text cannot grant authority.

Review whether untrusted documents/pages can cause the model to:

- reveal application data it was not authorized to access;
- call tools outside the user's permission;
- alter business state;
- send data to external destinations;
- bypass application policy;
- treat retrieved text as developer/system authority.

Use architectural separation, data provenance, tool authorization and output validation. Prompts can guide behavior but must not be the only enforcement control.

## 4. Tool and action authorization

For every model-callable tool/function:

- define the exact action and allowed arguments;
- enforce current user/service identity server-side;
- enforce object/tenant/role authorization inside the tool boundary;
- validate arguments with explicit schemas;
- derive protected fields such as actor/tenant/owner server-side;
- restrict external destinations and filesystem paths;
- make high-impact actions idempotent where appropriate;
- log actor, tool, target and outcome without sensitive prompt leakage.

The model choosing a tool does not authorize the action. A hidden tool description is not access control.

Avoid exposing generic shell, SQL, filesystem or unrestricted HTTP tools when narrow domain-specific tools can satisfy the product requirement.

## 5. Sensitive data and provider egress

Inventory what data is sent to external model providers. Check:

- secrets accidentally included in prompts/context;
- full database rows when only a subset is needed;
- cross-tenant context aggregation;
- private attachments/document text;
- logs/telemetry containing prompts/responses;
- provider retention/training settings only when project configuration/contract provides evidence.

Do not invent privacy/compliance claims about a provider. Use current official provider documentation when a decision depends on it.

## 6. RAG and document isolation

For retrieval systems, verify:

- ingestion requires proper authorization;
- document ownership/tenant metadata is authoritative;
- retrieval filters enforce tenant/user scope server-side;
- cache/vector namespaces cannot cross tenants;
- deleted/revoked documents stop appearing as intended;
- chunk metadata does not expose hidden source data;
- untrusted document instructions are treated as content, not authority;
- file parsing follows the file/parser security playbook;
- indexing pipeline cannot attach a document to another tenant via client-controlled metadata.

Test with at least two tenants/users when multi-tenant RAG is present.

## 7. Model output handling

Treat generated text as untrusted output. Review where it is rendered or executed:

- HTML/Markdown -> XSS/sanitization rules;
- URLs -> safe scheme/origin handling;
- SQL -> never execute raw model SQL against privileged production data without strict architecture/authorization and query controls;
- shell/code -> do not execute unrestricted generated commands/code;
- emails/messages -> prevent leakage and unintended recipients;
- file paths -> apply path controls;
- configuration/policy text -> require authoritative application validation.

Do not assume model-generated JSON is trustworthy because it parses.

## 8. Structured outputs and downstream sinks

Validate model/tool outputs with explicit schemas, bounds and enums before using them. Re-resolve identifiers against authorized server-side data. Reject unknown fields for privileged actions.

If the model proposes an object ID, payment amount, role, tenant ID, recipient, callback URL or command, the application must independently verify it.

## 9. Agent memory and cross-user isolation

Review conversation/memory stores for:

- user/tenant namespace in keys/queries;
- authorization on history retrieval;
- deletion/retention behavior required by product;
- accidental reuse of another user's context;
- summarization pipelines leaking hidden messages;
- cache keys that omit actor/tenant/model-policy dimensions.

A vector similarity match must still pass authorization filters.

## 10. Browsing, URL fetch, and SSRF

If the model can browse/fetch URLs, apply the outbound/SSRF controls from `ssrf-files-parsers.md`. The model must not be allowed to bypass destination policy by encoding, redirects, alternate host representations or indirect tool selection.

Do not forward internal credentials/cookies to arbitrary model-selected URLs.

## 11. Cost and resource abuse

AI endpoints can create denial-of-wallet risk. Review:

- authentication;
- per-user/tenant quota;
- input/token/file limits;
- maximum output/tool-loop count;
- concurrency;
- timeout/cancellation;
- retry behavior;
- expensive model selection;
- caching/deduplication where safe;
- queue controls for long-running jobs.

Do not load-test the provider. Validate limits using code and small bounded tests.

## 12. Model/provider credentials

Provider API keys are server secrets. Verify they are not shipped to browser/mobile code, embedded in prompts, stored in public config, logged, or committed. If browser-direct model access is a product requirement, use provider-supported short-lived/scoped mechanisms rather than exposing a long-lived server key.

## 13. Human confirmation and high-impact actions

For destructive/financial/external-communication actions, determine whether product requirements call for explicit human confirmation. If so, confirmation must bind to the exact pending action/parameters and authorization state, not a generic "approve" flag the model can fabricate.

Do not add confirmation theater to low-risk actions when normal server-side authorization is sufficient.

## 14. Logging and observability

Record enough to investigate AI actions:

- actor/tenant;
- model/tool name;
- tool target/action;
- policy decision;
- outcome/correlation ID;
- token/cost metrics if useful.

Avoid logging full sensitive prompts/responses by default. Apply redaction and data-minimization rules.

## 15. Security regression tests

Useful tests include:

- retrieved document from tenant B never appears in tenant A context;
- model-selected tool argument for another user's object is denied by server authorization;
- client cannot set actor/tenant/role through tool arguments;
- malformed/model-extra fields are rejected by schema;
- generated HTML/Markdown is safely rendered;
- model-selected external URL is constrained by outbound policy;
- maximum tool-loop/token/file limits are enforced;
- revoked document/session permission stops subsequent AI access as intended;
- provider key is absent from client build/static output.
