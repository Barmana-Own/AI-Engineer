# Windows Server deployment

This directory contains the reproducible runtime helpers for the AI Engineer control center on the Windows Server host.

Runtime layout:

- \`apps/control-center/dist\` is the IIS document root.
- \`/api/orchestrator/*\` is reverse-proxied to the loopback orchestrator on port 8012.
- \`/api/gateway/*\` is reverse-proxied to the loopback model gateway on port 8010.
- Ollama remains loopback-only on port 11434.
- The default model is \`qwen3:8b\`.

Prerequisites:

- Python 3.11 or newer with the three service virtual environments installed.
- Node.js 20 or newer for frontend builds.
- IIS URL Rewrite and Application Request Routing, already required by the host's existing proxy sites.
- Ollama with \`qwen3:8b\` available locally.

Start the services:

    .\deploy\windows-server\start-ai-engineer-server.ps1

Pull the model during first setup:

    .\deploy\windows-server\start-ai-engineer-server.ps1 -PullModel

Run the smoke checks:

    .\deploy\windows-server\health-check.ps1 -BaseUrl https://devoria.ir
    .\deploy\windows-server\health-check.ps1 -BaseUrl https://devoria.ir -Chat

The deployment script starts the three loopback services with control-plane and gateway authentication enabled. Autonomous execution is disabled by default and can be enabled only through protected machine environment variables; automatic remote Git pushes remain disabled by default. Configure tokens before starting a public deployment and run the authenticated health check after startup.
## Automatic startup

Register a Windows startup task and start the services immediately:

    .\deploy\windows-server\register-ai-engineer-task.ps1 -StartNow

The task starts only the loopback services, retries failed startup three times, and writes each service's stdout/stderr to logs\server\*.out.log and logs\server\*.err.log. Automatic remote Git pushes remain disabled; no GitHub credential is required for normal startup. If a separately reviewed release operation is later authorized, run it as an explicit operator action with a least-privilege account.

## Public deployment gate and rollback

Before a public restart:

1. Run the backend, gateway and local-agent test suites and build the Control Center.
2. Create and verify a timestamped backup of the current checkout and runtime data.
3. Configure `AI_ENGINE_CONTROL_PLANE_TOKEN`, `AI_ENGINE_OWNER_TOKEN` and `AI_ENGINE_GATEWAY_TOKEN` as protected machine environment variables. Do not put them in source, `.env.example`, logs or the frontend bundle.
4. Set `AI_ENGINE_AUTONOMOUS_MODE_ENABLED=false` and `AI_ENGINE_AUTONOMOUS_AUTO_PUSH=false` unless an owner-approved change explicitly requires otherwise.
5. Start/restart the services and run `health-check.ps1 -BaseUrl https://devoria.ir` (and `-Chat` only when a model smoke test is authorized).

If any health or smoke check fails, stop the new service instance, restore the verified checkout/data backup, restart the prior version and rerun the health checks. Do not delete the backup until the replacement has passed its checks.
