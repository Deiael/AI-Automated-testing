@echo off
setlocal
cd /d "%~dp0.."

echo [REA] Configure Cursor MCP + reverse-engineering skill
echo Project: %CD%
echo.

where node >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js not found. Install Node.js 22.19+ first.
  exit /b 1
)

npx -y rea-agents@latest setup --client cursor --yes
if errorlevel 1 (
  echo ERROR: REA setup failed.
  exit /b 1
)

echo.
echo [REA] Doctor check
npx -y rea-agents@latest doctor --client cursor --format json

echo.
echo Done. Restart Cursor, then open docs\REA.md for learning prompts.
exit /b 0
