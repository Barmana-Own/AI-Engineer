# Input Validation, Injection, Browser and Output Security

## Table of contents

1. Source-to-sink method
2. Validation and canonicalization
3. SQL/NoSQL injection
4. OS command/process execution
5. Template/expression injection
6. Deserialization and dynamic evaluation
7. XSS and HTML rendering
8. URL/redirect handling
9. CSRF
10. CORS
11. Browser security headers
12. Cache/content-type concerns
13. Testing approach

## 1. Source-to-sink method

Do not search only for "bad strings." For each risky sink, identify whether attacker-controlled data can reach it and what transformations/controls occur.

Common untrusted sources include HTTP parameters/body/headers/cookies, uploaded files, database content originally supplied by users, webhook/vendor data, queue messages, environment-controlled deployment metadata and filenames/URLs.

Common sensitive sinks include database query construction, shell/process invocation, dynamic template/expression evaluation, HTML/JS/CSS/URL contexts, redirects, filesystem paths and outbound URLs.

## 2. Validation and canonicalization

Use schema/type validation at trust boundaries. Validate semantics, not only syntax. Apply:

- type/shape;
- length/size;
- ranges;
- enum/allowlist values;
- identifier formats;
- nested object limits;
- collection/page limits;
- canonical representation where equivalent encodings can bypass policy.

Do not double-decode attacker input or apply inconsistent normalization between authorization and use.

Validation does not replace context-appropriate output encoding or parameterized APIs.

## 3. SQL/NoSQL injection

Require parameter binding/query builders/ORM APIs that separate code from data. Inspect raw-query escape hatches.

Check dynamic:

- `WHERE` values;
- sorting field/direction;
- column/table identifiers;
- `LIMIT/OFFSET` when constructed as text;
- search expressions;
- raw JSON/filter objects passed to NoSQL stores;
- operators supplied by clients.

Parameters often cannot bind SQL identifiers; use explicit allowlists/mappings for user-selectable sort/filter fields.

Do not consider manual quote escaping equivalent to parameterization.

## 4. OS command/process execution

Avoid shells for untrusted data. Prefer library APIs or process execution with an argument array and fixed executable. If a shell is unavoidable, redesign when possible; shell escaping is fragile and platform-dependent.

Inspect image/media/document tools, Git/system utilities, archive commands and user-controlled filenames/options. Prevent option injection where a filename beginning with `-` could become a flag.

## 5. Template/expression injection

Inspect server-side templates, expression languages, query DSLs and dynamic configuration. Untrusted content should be data, not executable template/code. Disable or avoid dynamic evaluation features not required by the product.

## 6. Deserialization and dynamic evaluation

Treat `eval`, dynamic code generation, unsafe YAML/object deserialization and loading attacker-controlled serialized objects as high-risk candidates. Confirm reachability and data origin before assigning a vulnerability.

Prefer safe parsers and explicit data schemas.

## 7. XSS and HTML rendering

Identify contexts:

- HTML text/attribute;
- URL attributes;
- JavaScript context;
- CSS context;
- rich-text/Markdown/HTML preview;
- server-rendered templates;
- client component rendering.

Prefer framework automatic escaping. Treat escape hatches (`dangerouslySetInnerHTML`, raw HTML templates, DOM `innerHTML`, HTML sanitizer bypasses) as review points.

If rich HTML is an explicit feature, use a maintained allowlist sanitizer appropriate to the runtime and validate URLs/protocols. Sanitization must occur at a trustworthy boundary and be tested against bypass-relevant cases.

Stored XSS can have higher impact when content is viewed by administrators or many users.

## 8. URL and redirect handling

For redirects/return URLs:

- prefer relative application paths;
- if external redirects are required, validate against explicit trusted origins/protocols;
- reject scheme-relative, encoded, credential-in-URL and parser-confusion forms as appropriate;
- use the platform URL parser, not substring checks.

For links rendered from untrusted input, restrict unsafe schemes such as `javascript:` and consider `rel` protections for new-window links.

## 9. CSRF

Determine whether credentials are automatically attached by the browser (especially cookies). For state-changing cookie-authenticated operations, require an appropriate CSRF defense such as framework tokens or robust same-origin/custom-header patterns plus suitable SameSite behavior.

Do not require CSRF tokens mechanically for bearer-token APIs where browsers do not automatically attach the credential; instead verify token storage and CORS/XSS risks.

Use safe HTTP methods for read-only actions. GET endpoints must not perform sensitive state changes.

## 10. CORS

CORS is a browser read-policy, not server authentication/authorization. Review:

- allowed origins;
- credential mode;
- origin reflection;
- wildcard behavior;
- preflight handling;
- allowed headers/methods;
- `null` origin handling if relevant;
- environment-specific origin configuration.

Never combine permissive/reflective origins with credentials without strict trusted-origin validation.

Server-to-server attackers are not constrained by CORS.

## 11. Browser security headers

Assess headers in context:

- Content-Security-Policy;
- frame-ancestor/clickjacking protection;
- MIME sniffing protection;
- Referrer-Policy;
- HSTS at the TLS termination layer when applicable;
- Permissions-Policy when relevant.

Do not report every missing optional header as a serious vulnerability. Connect the control to real exposure and deployment architecture.

CSP is defense in depth and should not be used instead of fixing XSS.

## 12. Cache and content-type concerns

Review whether authenticated/private responses can be cached publicly or across users. Ensure content types are correct for downloads and untrusted files. Consider `Content-Disposition` and nosniff behavior for user-uploaded active content.

Avoid serving user-controlled HTML/SVG from a trusted application origin unless intentionally sandboxed and safely handled.

## 13. Testing approach

Prefer targeted unit/integration tests that exercise security invariants without harmful payloads. Examples:

- parameterized query handles metacharacter-containing input as data;
- protected sort fields reject unknown identifier values;
- raw HTML feature sanitizes disallowed elements/attributes;
- external redirect input is rejected while valid local return path works;
- state-changing cookie endpoint rejects missing/invalid CSRF token;
- disallowed CORS origin receives no credentialed access headers.

Do not use large fuzzing or denial-of-service payloads by default.
