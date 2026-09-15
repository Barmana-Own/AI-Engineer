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

    .\deploy\windows-server\health-check.ps1
    .\deploy\windows-server\health-check.ps1 -Chat

The deployment script enables the bounded autonomous supervisor for the configured workspace, but keeps automatic Git pushes disabled. Autonomous changes stay on the server until server-side authentication, authorization, audit, backup, and rollback controls are complete.
## Automatic startup

Register a Windows startup task and start the services immediately:

    .\deploy\windows-server\register-ai-engineer-task.ps1 -StartNow

The task runs as LocalSystem, starts only the loopback services, retries failed startup three times, and writes startup output to logs\server\startup-task.log.