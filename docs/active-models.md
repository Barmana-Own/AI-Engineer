# Active models and provider routing

This is the current runtime map for the local AI Engineer stack. Values that
can be changed through environment variables are shown as defaults; the
running gateway exposes the effective values at `GET /v1/runtime/models`.

## Components

| Component | Current model/provider | Role |
| --- | --- | --- |
| Orchestrator | `AGENT_MODEL` (default `qwen2.5-coder:3b`) | Chooses structured tool calls for coding tasks. Requests are sent to the model gateway. |
| Model Gateway (`:8010`) | Local Ollama by default; embedded Provider Hub when its upstream probe is healthy | OpenAI-compatible chat boundary, model catalog cache, retries, cross-provider fallback routing, and usage accounting. |
| Local Agent (`:8011`) | No language model | Executes the orchestrator's approved file, terminal, process, and Git actions inside an allowed workspace. |
| Provider Router (`:8020`) | Embedded FreeLLMAPI-compatible proxy | Exposes OpenAI Chat Completions and Codex-compatible Responses at `/v1/responses`. The launcher starts it without exposing its unified key; it becomes the gateway upstream only after a live provider/model health probe passes. |

## Gateway candidate order

For each chat request, the Python gateway builds a de-duplicated candidate list:

1. The request's `model`, or `DEFAULT_MODEL` when omitted.
2. Any request-level `fallback_models`.
3. `FALLBACK_MODELS` from the gateway environment.

The list is capped at `MAX_FALLBACK_ATTEMPTS`. The gateway retries the same
candidate up to `MAX_RETRIES` before trying the next one. It falls back for
timeouts, temporary provider outages, rate limits, and provider responses that
identify an unavailable model. A successful response includes the selected and
attempted models in its `gateway` metadata; usage is recorded in
`data/model-gateway/usage.sqlite3`.

The runtime endpoint reports this effective configuration without returning API
keys. `GET /v1/models` remains the endpoint for the provider's live model
catalog (with a short local cache).

The root launcher keeps the Provider Router available for Codex/Responses
clients, but does not mistake a catalogue-only or rate-limited upstream for a
working model. When `/v1/providers` reports a temporary rate limit or no
healthy provider, the gateway stays on the local Ollama model and the proxy
remains ready for a later retry. This makes the free local path reliable while
still allowing the embedded proxy to take over automatically when it recovers.

Completed autonomous cycles create a local Git checkpoint first. The
supervisor then pushes only a clean `main` branch to the configured
`Barmana-Own/AI-Engineer` origin; a different remote, uncommitted tree, or
failed authentication is skipped and logged without interrupting the next
cycle.

## Optional provider profiles

The gateway can add OpenAI-compatible providers without importing vendor SDKs.
Set `PROVIDER_PROFILES_JSON` in the local, ignored `.env` and reference secrets
with `api_key_env`. Qualified model names route to the selected provider:
`openrouter/openai/gpt-4o-mini`, `gemini/gemini-2.5-flash`, or
`openai/gpt-4o-mini`. Unqualified names continue to use the local Barmana/Ollama
default. Profiles are skipped when their environment key is absent.

## Current defaults

```text
AGENT_MODEL=qwen2.5-coder:3b
DEFAULT_MODEL=qwen2.5-coder:3b
FALLBACK_MODELS=
MAX_FALLBACK_ATTEMPTS=1
MAX_RETRIES=1
```
