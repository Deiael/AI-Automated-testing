@echo off
chcp 65001 >nul
echo ============================================
echo  AI-Test: 清理 C 盘缓存 + 安装依赖 + 启动
echo  项目目录: D:\AI-test
echo ============================================
echo.

set TEMP=D:\AI-test\.cache\tmp
set TMP=D:\AI-test\.cache\tmp
set TMPDIR=D:\AI-test\.cache\tmp
set PIP_CACHE_DIR=D:\AI-test\.cache\pip
set NPM_CONFIG_CACHE=D:\AI-test\.cache\npm

mkdir D:\AI-test\.cache\tmp 2>nul
mkdir D:\AI-test\.cache\pip 2>nul
mkdir D:\AI-test\.cache\npm 2>nul

echo [1/5] 清理 C 盘临时缓存（跳过占用中的文件）...
del /q /f /s "%LOCALAPPDATA%\Temp\*.*" >nul 2>nul
for /d %%i in ("%LOCALAPPDATA%\Temp\*") do rd /s /q "%%i" >nul 2>nul
if exist "%LOCALAPPDATA%\npm-cache" rd /s /q "%LOCALAPPDATA%\npm-cache" >nul 2>nul
if exist "%LOCALAPPDATA%\pip\Cache" rd /s /q "%LOCALAPPDATA%\pip\Cache" >nul 2>nul

echo [2/5] 检查 C 盘剩余空间...
fsutil volume diskfree C:

set PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
if not exist "%PY%" (
  echo 未找到 Python 3.11: %PY%
  pause
  exit /b 1
)

echo [3/5] 创建 D 盘虚拟环境并安装依赖...
if not exist "D:\AI-test\.venv\Scripts\python.exe" (
  "%PY%" -m venv "D:\AI-test\.venv"
)
"D:\AI-test\.venv\Scripts\python.exe" -m pip install --upgrade pip --cache-dir D:\AI-test\.cache\pip
"D:\AI-test\.venv\Scripts\python.exe" -m pip install --cache-dir D:\AI-test\.cache\pip -e D:\AI-test\packages\contracts
"D:\AI-test\.venv\Scripts\python.exe" -m pip install --cache-dir D:\AI-test\.cache\pip -r D:\AI-test\engine\requirements.txt
"D:\AI-test\.venv\Scripts\python.exe" -m pip install --cache-dir D:\AI-test\.cache\pip -r D:\AI-test\gateway\requirements.txt

echo [4/5] 前端依赖...
cd /d D:\AI-test\frontend
if not exist node_modules\vue (
  call npm install --cache D:\AI-test\.cache\npm
)

if not exist D:\AI-test\engine\.env copy D:\AI-test\engine\.env.example D:\AI-test\engine\.env
if not exist D:\AI-test\gateway\.env copy D:\AI-test\gateway\.env.example D:\AI-test\gateway\.env
mkdir D:\AI-test\gateway\data 2>nul

echo [5/5] 启动三层服务（新窗口）...
start "AI-Test Engine :8200" cmd /k "set TEMP=D:\AI-test\.cache\tmp&& set TMP=D:\AI-test\.cache\tmp&& cd /d D:\AI-test\engine && D:\AI-test\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8200"
timeout /t 2 /nobreak >nul
start "AI-Test Gateway :8100" cmd /k "set TEMP=D:\AI-test\.cache\tmp&& set TMP=D:\AI-test\.cache\tmp&& cd /d D:\AI-test\gateway && D:\AI-test\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8100"
timeout /t 2 /nobreak >nul
start "AI-Test Frontend :5190" cmd /k "set TEMP=D:\AI-test\.cache\tmp&& set TMP=D:\AI-test\.cache\tmp&& set NPM_CONFIG_CACHE=D:\AI-test\.cache\npm&& cd /d D:\AI-test\frontend && npm run dev"

echo.
echo 完成。浏览器打开: http://localhost:5190
echo API Key: dev-key
echo 网关健康: http://localhost:8100/health
echo 引擎健康: http://localhost:8200/health
echo.
pause
