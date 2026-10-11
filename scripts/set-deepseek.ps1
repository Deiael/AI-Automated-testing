param(
  [Parameter(Mandatory = $true)][string]$ApiKey,
  [string]$BaseUrl = "https://api.deepseek.com/v1",
  [string]$Model = "deepseek-chat"
)

$Root = Split-Path $PSScriptRoot -Parent
$EnvFile = Join-Path $Root "engine\.env"
@"
ENGINE_HOST=0.0.0.0
ENGINE_PORT=8200
OPENAI_API_KEY=$ApiKey
OPENAI_BASE_URL=$BaseUrl
OPENAI_MODEL=$Model
ALLOW_MODEL_OVERRIDE=false
LLM_FALLBACK_MOCK=false
LLM_TIMEOUT_SECONDS=90
LLM_TEMPERATURE=0.2
"@ | Set-Content -Path $EnvFile -Encoding UTF8

Write-Host "Wrote $EnvFile"
Write-Host "Please restart engine process, then check: http://127.0.0.1:8200/health"
Write-Host 'Expect: "llm_enabled": true'
