$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location "$Root\frontend"
if (-not (Test-Path node_modules)) { npm install }
npm run dev
