# Release Packaging Policy

The final archive should contain what a competent recipient needs to build/run/deploy the approved project, without private local state or secrets.

## Default exclusions

Exclude by default:
- `.git/` and VCS internals;
- `.final-review/` audit working logs/state unless explicitly requested;
- `node_modules/`, package caches, virtualenvs and dependency caches;
- editor/OS metadata;
- coverage outputs unless explicitly deliverable;
- temp/log files;
- local runtime PIDs/sockets;
- local databases and database dumps unless they are intentional sanitized fixtures;
- backups containing user/private data;
- `.env` and environment-specific secret files;
- private keys/certificates not explicitly public/test fixtures;
- cloud/provider credentials;
- local build caches.

## Environment templates

Allow clearly non-secret templates such as:
- `.env.example`;
- `.env.sample`;
- `.env.template`.

Inspect them to ensure they contain placeholders and safe defaults.

## Build artifacts

Whether to include built artifacts depends on release contract:
- source delivery: include source + lockfiles + build instructions; build output optional;
- binary/static release: include required built output after verifying it matches current source;
- container release: include Docker/compose/manifest files and, if image export is requested/supported, verify provenance separately.

Do not include stale build artifacts that can be mistaken for current output.

## Sensitive-content rule

Filtering a secret out of the ZIP is not sufficient if the secret remains hardcoded in source that must be delivered. Fix the source/config and rotate compromised real credentials when appropriate.

## Allowlist

`scan_release_hygiene.py` can consume a narrow JSON allowlist. Each entry should include:
- rule ID;
- exact path;
- reason;
- optional fingerprint when available.

Use allowlists only for confirmed false positives or intentionally public/test material. Never broadly suppress an entire rule to hide a real issue.

## Archive verification

After packaging:
1. list archive members;
2. verify required source/manifests/docs exist;
3. verify forbidden sensitive paths do not exist;
4. optionally extract to a temporary directory and perform a smoke/build from the extracted artifact when feasible;
5. record archive SHA-256 and size in release manifest.
