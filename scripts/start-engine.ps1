$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$env:TEMP = Join-Path $Root ".cache\tmp"
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "请先运行 CLEAN-C-AND-SETUP.cmd 创建虚拟环境" }
Set-Location (Join-Path $Root "engine")
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& $Py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8200
