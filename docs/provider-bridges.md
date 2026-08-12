# Optional local provider bridges

The model gateway already speaks the OpenAI-compatible chat contract. The
repositories below can therefore be used as optional localhost sidecars; they
are not copied into AI Engineer and they do not create free model capacity by
themselves.

| Bridge | What it provides | Default endpoint | Credential requirement |
| --- | --- | --- | --- |
| [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) | OAuth/account-pool proxy for Codex, Gemini, Claude and Grok | `http://127.0.0.1:8317/v1` | A locally configured API key and the user's own OAuth/account entitlement |
| [codex-proxy](https://github.com/icebear0828/codex-proxy) | Codex Responses-compatible proxy and optional OpenAI-compatible providers | `http://127.0.0.1:8080/v1` | Local proxy key plus a user-owned ChatGPT account or configured provider |
| [codex2api](https://github.com/james-6-23/codex2api) | Codex account-pool gateway with Chat/Responses/Messages routes | `http://127.0.0.1:8080/v1` | Imported user refresh/access token or another configured upstream |
| [Sub2API](https://github.com/Wei-Shaw/sub2api) | Subscription/API-key distribution gateway for several providers | `http://127.0.0.1:8080/v1` | User-owned subscription/OAuth account or API key |
| [awesome-codex-skills](https://github.com/composio-community/awesome-codex-skills) | A curated list of instruction bundles, not an inference API | — | No provider credential; skills must be reviewed before installation |

## Configure one bridge

All bridge profiles are disabled in `.env.example`. Copy the JSON into the
ignored `services/model-gateway/.env`, set exactly one entry to `enabled:true`,
and place the local sidecar key in the matching environment variable:

```dotenv
LOCAL_BRIDGE_PROFILES_JSON={"cliproxyapi":{"enabled":true,"base_url":"http://127.0.0.1:8317/v1","api_key_env":"CLIPROXYAPI_API_KEY"}}
CLIPROXYAPI_API_KEY=your-local-bridge-key
DEFAULT_MODEL=cliproxyapi/<model-returned-by-v1-models>
```

Restart the model gateway, then verify `GET /health/ready` and
`GET /v1/models`. The normal local Ollama provider remains available as the
default when no bridge profile is enabled. Bridge names are qualified in model
requests (`cliproxyapi/model`, `codexproxy/model`, and so on), so a sidecar is
never selected accidentally.

## Safety and licensing

Keep every sidecar bound to `127.0.0.1`; do not expose OAuth tokens or bridge
keys in Git, logs, prompts, or the project database. The repositories have
different terms: `codex2api` advertises MIT, CLIProxyAPI advertises MIT,
Sub2API is LGPL-3.0 and warns about upstream terms of service, while
`codex-proxy` is explicitly non-commercial. Review the upstream license and
provider terms before enabling a bridge. AI Engineer only implements the
standard compatible client and does not automate token extraction or bypass
provider limits.
