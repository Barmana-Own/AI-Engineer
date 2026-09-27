from pathlib import Path

path = Path(r"C:\Services\AI-Engineer\current\deploy/windows-server/health-check.ps1")
text = path.read_text(encoding="utf-8")
marker = "$controlToken = Get-RequiredSecret \"AI_ENGINE_CONTROL_PLANE_TOKEN\""
function = r'''function Invoke-GatewayModelsCheck([string]$Name, [string]$Url, [hashtable]$Headers = @{}) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Headers $Headers -TimeoutSec 20
        if ($response.StatusCode -ne 200) { throw "HTTP $($response.StatusCode)" }
        $payload = $response.Content | ConvertFrom-Json
        if (-not $payload.provider -or -not $payload.default_model) {
            throw "gateway model catalog response is missing provider/default_model."
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
    raise SystemExit("health insertion marker not found")
text = text.replace(marker, function + marker, 1)
old_call = 'Invoke-JsonCheck "Gateway Proxy" "$BaseUrl/api/gateway/v1/runtime/models" "" $gatewayHeaders | Out-Null'
new_call = 'Invoke-GatewayModelsCheck "Gateway Proxy" "$BaseUrl/api/gateway/v1/runtime/models" $gatewayHeaders | Out-Null'
if old_call not in text:
    raise SystemExit("gateway health call not found")
text = text.replace(old_call, new_call, 1)
path.write_text(text, encoding="utf-8", newline="")
print("fixed gateway health response validation")
