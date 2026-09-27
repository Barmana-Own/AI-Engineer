# Scope, Authorization, and Safe Testing

## Table of contents

1. Scope classes
2. Default authorization rules
3. Dynamic-testing decision tree
4. Prohibited actions
5. Production handling
6. Third-party systems
7. Sensitive evidence handling
8. Blocker rules

## 1. Scope classes

Classify every target before active testing:

- `SOURCE_ONLY`: repository/configuration/documentation only.
- `LOCAL`: localhost, local containers, ephemeral test services created from the project.
- `DEV_TEST_AUTHORIZED`: a development or test environment explicitly owned/authorized for security testing.
- `PRODUCTION_AUTHORIZED`: a production environment for which the user explicitly authorized the specific active test.
- `THIRD_PARTY`: vendor, payment provider, SaaS, identity provider, external API or infrastructure not controlled by the project.
- `UNKNOWN`: ownership/authorization cannot be established.

Store the classification in the report.

## 2. Default authorization rules

The active repository and local execution of that repository are authorized defensive scope. A URL, API key, hostname, cloud account ID, webhook endpoint or production configuration in source does not grant authorization to test that remote target.

For `THIRD_PARTY` or `UNKNOWN`, perform only passive/documentation review and local/mocked verification unless the user provides explicit authorization.

## 3. Dynamic-testing decision tree

Before sending a security-oriented request:

1. Identify the exact host/service and environment.
2. Determine the scope class.
3. Determine whether the test is non-destructive and low-volume.
4. Confirm the request will not alter real customer/business data unless the environment is purpose-built for testing.
5. Confirm no brute force, load generation, persistence, exfiltration or destructive payload is required.
6. Use a dedicated test account/data set when authentication is needed.
7. Record the method and result without storing live credentials.

If any step cannot be satisfied, reproduce locally or use code/data-flow analysis instead.

## 4. Prohibited actions

Do not:

- perform denial-of-service or resource-exhaustion attacks;
- brute-force real accounts or credentials;
- attempt persistence or post-exploitation;
- steal or export data to prove impact;
- access another real user's records to prove authorization failure;
- deploy malware or callbacks to uncontrolled infrastructure;
- bypass payment or financial controls against real providers;
- exploit third-party systems;
- disable monitoring or evade detection;
- use destructive database/file operations for proof.

Prove security defects using the minimum safe evidence necessary.

## 5. Production handling

Production is source/configuration review by default. Active production testing requires explicit authorization for the specific target and should use the least-invasive method. Prefer a local or staging reproduction. Never create avoidable customer impact to increase confidence.

## 6. Third-party systems

For OAuth/OIDC, payment, SMS, email, storage, analytics and other vendors:

- review local integration code and vendor configuration expectations;
- validate signatures/tokens locally with fixtures when possible;
- use official documentation for protocol behavior;
- do not probe vendor infrastructure for weaknesses;
- separate project-control findings from vendor risk.

## 7. Sensitive evidence handling

For secrets and personal data:

- never record the complete value;
- record file path, line or configuration key;
- use a redacted prefix/suffix or one-way fingerprint only if correlation is needed;
- do not place sensitive values in command history, screenshots, reports or test fixtures;
- recommend rotation when a real credential has been committed or exposed.

## 8. Blocker rules

Use `BLOCKED` only when a required security decision cannot be verified without an unavailable external dependency such as:

- required credentials to an authorized test environment;
- required private protocol/API contract;
- required legal/business approval for a security-sensitive behavior;
- an unavailable external system that cannot be safely mocked and whose behavior is essential to the gate.

Do not use `BLOCKED` for ordinary engineering work, missing tests that can be written, unclear code that can be inspected, or a fix that is merely difficult. Those remain work to perform or become `FAIL` if unresolved.
