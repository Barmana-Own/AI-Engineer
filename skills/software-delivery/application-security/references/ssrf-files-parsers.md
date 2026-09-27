# SSRF, Outbound Requests, Webhooks, Files, Paths, Archives, and Parsers

## Table of contents

1. Outbound request inventory
2. SSRF defenses
3. Redirect/DNS/address considerations
4. Webhooks and callbacks
5. File upload pipeline
6. File download/private object authorization
7. Path traversal
8. Archive extraction
9. Parser/transformation safety
10. Image/document/media processing
11. Storage and signed URLs
12. Regression tests

## 1. Outbound request inventory

Find every feature where untrusted or semi-trusted input can influence a server-side destination:

- URL preview/import;
- webhook testing;
- image/document fetch;
- PDF generation from URLs;
- callback URLs;
- OAuth metadata/JWKS discovery when dynamically configured;
- proxy endpoints;
- redirects followed by server clients;
- vendor URLs stored in database;
- background workers fetching user-provided resources.

Trace initial request and every redirect/follow-up fetch.

## 2. SSRF defenses

Prefer architectural allowlists: fixed service endpoints, known provider hosts or project-controlled resource IDs rather than arbitrary URLs.

When arbitrary external HTTP(S) fetch is a product requirement, consider:

- allow only required schemes;
- parse with a standard URL parser;
- reject embedded credentials when unnecessary;
- constrain ports if possible;
- resolve and reject loopback/private/link-local/internal/metadata destinations according to environment and requirement;
- re-check destination across redirects;
- limit redirect count;
- set connection/read/overall timeouts;
- cap response size;
- avoid forwarding sensitive internal headers/cookies;
- isolate fetcher network privileges when architecture permits.

Do not claim a complete SSRF defense based only on a hostname regex.

## 3. Redirect, DNS, and address considerations

Hostname allowlists should compare normalized parsed hostnames, not suffix substrings such as `endsWith("trusted.com")` that may accept `eviltrusted.com`.

Be aware that DNS resolution and redirects can change the final network destination. Where the threat model includes access to internal services, enforce policy on the actual connection destination through a trusted network-aware control or equivalent robust mechanism.

Avoid implementing complex IP canonicalization from scratch when a maintained network/url library can do it.

## 4. Webhooks and callbacks

For inbound webhooks:

- verify cryptographic signature/MAC using provider guidance;
- use the correct raw body representation if the signature scheme requires it;
- validate timestamp/age when protocol provides it;
- use constant-time comparison through a library where appropriate;
- bind event/provider/account identifiers as required;
- deduplicate event IDs / enforce idempotency;
- authorize resulting object/state changes independently where appropriate;
- treat webhook payload fields as untrusted data even after authenticity verification;
- log verification outcome without storing secrets/full sensitive payloads.

A shared secret in a query parameter is usually more leak-prone than a signed request/header scheme.

For outbound callbacks, validate destination according to SSRF rules if user-configurable.

## 5. File upload pipeline

Inventory all upload entry points and downstream consumers. Review:

- authentication/authorization;
- maximum request/file/count size;
- allowed content types and business-required extensions;
- content signature/type validation where meaningful;
- filename handling;
- random/server-generated storage keys;
- duplicate/overwrite behavior;
- active-content risks;
- malware scanning hook where risk/requirements warrant it;
- image/document re-encoding if used as a control;
- private vs public storage;
- metadata leakage;
- asynchronous processing and worker validation;
- cleanup of rejected/temporary files.

Do not rely solely on client-supplied MIME type or extension.

File scanning is not a substitute for authorization, size limits or safe serving.

## 6. File download and private object authorization

A hard-to-guess URL/key is not authorization. Verify the current caller is allowed to access the object before returning bytes or a signed URL.

Check:

- object ID -> owner/tenant resolution;
- signed URL TTL and scope;
- content disposition;
- range requests if they interact with authorization/cost;
- cached responses;
- deleted/revoked object access;
- thumbnails/derived files inheriting correct privacy.

## 7. Path traversal

Avoid joining raw user input into filesystem paths. Prefer opaque object IDs mapped to server-owned paths.

Where relative paths are a requirement:

- normalize/canonicalize using platform path APIs;
- resolve against a fixed base;
- verify final path remains under the allowed base;
- consider symlinks where relevant;
- do not trust extension filtering to prevent traversal;
- apply the same control to read, write, delete, rename and archive operations.

Review encoded separators and platform-specific path behavior where relevant, but do not add brittle handcrafted decoding loops.

## 8. Archive extraction

Treat archive entry names as untrusted. Prevent archive traversal (Zip Slip equivalent) by resolving each entry destination and ensuring it remains under the extraction directory. Also consider:

- symlink/hardlink entries;
- absolute paths;
- file-count and expanded-size limits;
- nested archive/resource exhaustion;
- overwrite behavior;
- permissions/ownership metadata;
- cleanup on failure.

Do not test archive bombs with resource-exhausting files. Validate limits from code and small fixtures.

## 9. Parser/transformation safety

For XML/YAML/CSV/Markdown/PDF/image/template parsers, identify whether untrusted input can trigger:

- external entity/network/file access;
- unsafe object construction;
- formula injection in exported spreadsheets;
- active HTML/JS in rendered content;
- excessive resource use;
- command invocation through conversion tools;
- parser-specific unsafe mode.

Use safe parser modes and maintained libraries.

## 10. Image/document/media processing

Review wrappers around ImageMagick/FFmpeg/LibreOffice/Pandoc/headless browsers or similar tools. Prefer argument arrays, sandboxing/limited privileges, timeouts, file-size limits and controlled input/output paths. Avoid shell command construction with filenames or options.

Generated previews/thumbnails must preserve source-object authorization.

## 11. Storage and signed URLs

For S3-compatible storage/MinIO/cloud object stores:

- keep private data private by default;
- review bucket/policy configuration in repository;
- use narrowly scoped signed URLs with appropriate TTL;
- do not let client choose arbitrary bucket/key for privileged operations;
- bind metadata/object ownership in application data;
- avoid exposing storage admin credentials to frontend;
- ensure object deletion/update authorization;
- consider orphaned objects after transaction failure.

## 12. Regression tests

Create focused tests such as:

- unauthorized user cannot obtain private file/signed URL;
- path input resolves only inside allowed base;
- disallowed outbound host/scheme is rejected while valid allowlisted URL works;
- redirect to disallowed destination is rejected if redirects are followed;
- webhook with invalid signature has no side effect;
- duplicate webhook event has one side effect;
- oversized/file-count request is rejected without storing partial object;
- archive entry attempting parent traversal is rejected using a tiny safe fixture.
