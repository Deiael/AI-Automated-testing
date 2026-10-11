#Requires -Version 5.1
$ErrorActionPreference = "Continue"
$Root = Split-Path $PSScriptRoot -Parent
$Cache = Join-Path $Root ".cache"
$Tmp = Join-Path $Cache "tmp"
$PipCache = Join-Path $Cache "pip"
$NpmCache = Join-Path $Cache "npm"
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$SysPy = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"

New-Item -ItemType Directory -Force -Path $Tmp, $PipCache, $NpmCache | Out-Null
$env:TEMP = $Tmp
$env:TMP = $Tmp
$env:TMPDIR = $Tmp
$env:PIP_CACHE_DIR = $PipCache
$env:NPM_CONFIG_CACHE = $NpmCache

Write-Host "==> Free some C: temp (best-effort)"
$cTemp = Join-Path $env:LOCALAPPDATA "Temp"
Get-ChildItem $cTemp -ErrorAction SilentlyContinue | ForEach-Object {
  Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}
$npmOld = Join-Path $env:LOCALAPPDATA "npm-cache"
if (Test-Path $npmOld) {
  Remove-Item $npmOld -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "==> Create venv on D:"
if (-not (Test-Path $VenvPy)) {
  if (-not (Test-Path $SysPy)) { throw "Python 3.11 not found at $SysPy" }
  & $SysPy -m venv (Join-Path $Root ".venv")
}

Write-Host "==> Install Python deps into D:\AI-test\.venv"
& $VenvPy -m pip install --upgrade pip --cache-dir $PipCache
& $VenvPy -m pip install --cache-dir $PipCache -e (Join-Path $Root "packages\contracts")
& $VenvPy -m pip install --cache-dir $PipCache -r (Join-Path $Root "engine\requirements.txt")
& $VenvPy -m pip install --cache-dir $PipCache -r (Join-Path $Root "gateway\requirements.txt")

Write-Host "==> Frontend npm install (cache on D:)"
Push-Location (Join-Path $Root "frontend")
if (-not (Test-Path "node_modules\vue")) {
  npm install --cache $NpmCache
}
Pop-Location

if (-not (Test-Path (Join-Path $Root "engine\.env"))) {
  Copy-Item (Join-Path $Root "engine\.env.example") (Join-Path $Root "engine\.env")
}
if (-not (Test-Path (Join-Path $Root "gateway\.env"))) {
  Copy-Item (Join-Path $Root "gateway\.env.example") (Join-Path $Root "gateway\.env")
}
New-Item -ItemType Directory -Force -Path (Join-Path $Root "gateway\data") | Out-Null

Write-Host "==> Starting engine :8200"
Start-Process -FilePath $VenvPy -ArgumentList @("-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8200") -WorkingDirectory (Join-Path $Root "engine") -WindowStyle Normal

Start-Sleep -Seconds 2
Write-Host "==> Starting gateway :8100"
Start-Process -FilePath $VenvPy -ArgumentList @("-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8100") -WorkingDirectory (Join-Path $Root "gateway") -WindowStyle Normal

Start-Sleep -Seconds 2
Write-Host "==> Starting frontend :5190"
Start-Process -FilePath "npm" -ArgumentList @("run","dev") -WorkingDirectory (Join-Path $Root "frontend") -WindowStyle Normal

Write-Host ""
Write-Host "Open http://localhost:5190  (API Key: dev-key)"
Write-Host "Health: http://localhost:8100/health  http://localhost:8200/health"
