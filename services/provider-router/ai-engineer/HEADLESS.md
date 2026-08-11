# AI Engineer Provider Hub — Headless Mode

Start:

```powershell
Set-Location "F:\AI-Engineer\services\provider-router"

powershell -NoProfile -ExecutionPolicy Bypass `
  -File ".\ai-engineer\start-headless.ps1" `
  -Restart
```

Status:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File ".\ai-engineer\status-headless.ps1"
```

Stop:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File ".\ai-engineer\stop-headless.ps1"
```

Local endpoints:

```text
Status: http://127.0.0.1:8020
API:    http://127.0.0.1:8020/v1
```

No Vite dashboard or port 5173 is used.