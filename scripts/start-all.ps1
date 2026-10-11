$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  Write-Host "Missing venv. Run: python -m venv .venv && .\.venv\Scripts\pip install -e packages\contracts -r engine\requirements.txt -r gateway\requirements.txt"
  exit 1
}
$env:TEMP = Join-Path $Root ".cache\tmp"
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP, (Join-Path $Root "gateway\data") | Out-Null

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\engine'; & '$Py' -m uvicorn app.main:app --host 127.0.0.1 --port 8200"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\gateway'; & '$Py' -m uvicorn app.main:app --host 127.0.0.1 --port 8100"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\frontend'; npm run dev -- --host 127.0.0.1 --port 5190"
Write-Host "Started: engine:8200 gateway:8100 frontend:5190"
