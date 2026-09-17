# Configuration and Portability

## Authority

Runtime configuration remains service-scoped so the Orchestrator, Model Gateway, and Local Agent keep their existing deployment boundaries. The Orchestrator `Settings` model is authoritative for autonomous-run controls; the Gateway and Local Agent models own only service-specific options. Shared path behavior is defined by the environment precedence below and is implemented consistently by all three services.

## Project root precedence

1. `AI_ENGINE_PROJECT_ROOT` (preferred explicit override)
2. `PROJECT_ROOT` (backward-compatible alias)
3. Runtime discovery: walk parents of the service module until a directory containing both `services/` and `apps/` is found
4. The module's repository-relative fallback

The root is resolved at process startup. It must be an absolute path in production launchers. The same value is exported to child services by the Windows launcher.

## Shared path variables

| Variable | Scope | Default |
| --- | --- | --- |
| `AI_ENGINE_PROJECT_ROOT` | All services and desktop | Runtime discovery |
| `PROJECT_ROOT` | Legacy alias for the root | Unset |
| `WORKSPACE_ROOT` | Local Agent workspaces | <root>/workspaces |
| `SELF_WORKSPACE_ROOT` | Local Agent self workspace | <root> |
| `AUTONOMOUS_REPO_ROOT` | Orchestrator repository override | <root> |
| `AUTONOMOUS_WORKSPACE` | Named workspace alias | `ai-engineer` |

The desktop process uses the same root variables and otherwise resolves three levels above its Electron entrypoint. No source code assumes a specific drive letter.

## Autonomous safety defaults

- `AUTONOMOUS_MODE_ENABLED` defaults to `false`.
- `AUTONOMOUS_AUTO_PUSH` defaults to `false`; enabling it is an explicit deployment decision.
- The Windows server launcher propagates `AI_ENGINE_PROJECT_ROOT` to every service and starts with auto-push disabled.
- Existing environment variable names remain accepted by Pydantic settings. Unknown variables are ignored to preserve deployment compatibility.

## Service defaults

- Orchestrator: 127.0.0.1:8012, gateway URL 8010, Local Agent URL 8011.
- Model Gateway: 127.0.0.1:8010 with its cache and usage database below <root>/data/model-gateway.
- Local Agent: 127.0.0.1:8011 with process registry below <root>/data/local-agent and managed logs below <root>/logs/managed-processes.

## Deprecated values

Hard-coded values such as `F:\\AI-Engineer` are deprecated and no longer appear in launchers or environment examples. Replace them with `AI_ENGINE_PROJECT_ROOT` (or the legacy `PROJECT_ROOT` alias) when relocating a checkout. `AUTONOMOUS_REPO_ROOT` remains supported for an explicit repository override but should normally be omitted.

## Validation

Run each service from any checkout path after exporting `AI_ENGINE_PROJECT_ROOT`. The configuration tests verify root override precedence and the disabled auto-push default. Launchers resolve their own script location when no override is provided.
