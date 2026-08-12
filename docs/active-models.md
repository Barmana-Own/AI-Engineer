# Active models and provider routing

This is the current runtime map for the local AI Engineer stack. Values that
can be changed through environment variables are shown as defaults; the
running gateway exposes the effective values at `GET /v1/runtime/models`.

## Components

| Component | Current model/provider | Role |
| --- | --- | --- |
| Orchestrator | `AGENT_MODEL` (default `qwen2.5-coder:3b`) | Chooses structured tool calls for coding tasks. Requests are sent to the model gateway. |
| Model Gateway (`:8010`) | Barmana plus optional OpenAI-compatible provider pool | OpenAI-compatible chat boundary, model catalog cache, retries, cross-provider fallback routing, and usage accounting. |
| Local Agent (`:8011`) | No language model | Executes the orchestrator's approved file, terminal, process, and Git actions inside an allowed workspace. |
| Provider Router | Optional standalone FreeLLMAPI service | Has its own provider catalog and fallback features, but is not the provider used by the Python model gateway unless explicitly wired in. |

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
DEFAULT_MODEL=mistral-small-latest
FALLBACK_MODELS=mistral-medium-latest,auto,codestral-latest
MAX_FALLBACK_ATTEMPTS=3
MAX_RETRIES=1
```
