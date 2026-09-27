from pathlib import Path

path = Path(r"C:\Services\AI-Engineer\current\deploy/windows-server/health-check.ps1")
text = path.read_text(encoding="utf-8")
marker = "$controlToken = Get-RequiredSecret \"AI_ENGINE_CONTROL_PLANE_TOKEN\""
function = r'''function Invoke-CapabilitiesCheck([string]$Name, [string]$Url, [hashtable]$Headers = @{}) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Headers $Headers -TimeoutSec 20
        if ($response.StatusCode -ne 200) { throw "HTTP $($response.StatusCode)" }
        $payload = $response.Content | ConvertFrom-Json
        if ($payload.service -notlike "*Orchestrator*" -or $payload.workspace_guarded -ne $true -or $payload.mutation_requires_checkpoint -ne $true) {
            throw "orchestrator capabilities response failed safety assertions."
        }
        Write-Host ("PASS {0} ({1})" -f $Name, $response.StatusCode) -ForegroundColor Green
        return $payload
    }
    catch {
        Write-Host ("FAIL {0}: {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
        throw
    }
}

'''
if marker not in text:
    raise SystemExit("capabilities insertion marker not found")
text = text.replace(marker, function + marker, 1)
old_call = 'Invoke-JsonCheck "Authenticated Orchestrator" "$BaseUrl/api/orchestrator/capabilities" "Orchestrator" $controlHeaders | Out-Null'
new_call = 'Invoke-CapabilitiesCheck "Authenticated Orchestrator" "$BaseUrl/api/orchestrator/capabilities" $controlHeaders | Out-Null'
if old_call not in text:
    raise SystemExit("capabilities health call not found")
path.write_text(text.replace(old_call, new_call, 1), encoding="utf-8", newline="")
print("fixed capabilities health response validation")
