@echo off
chcp 65001 >nul
set TEMP=D:\AI-test\.cache\tmp
set TMP=D:\AI-test\.cache\tmp
set PIP_CACHE_DIR=D:\AI-test\.cache\pip
mkdir D:\AI-test\.cache\tmp 2>nul
mkdir D:\AI-test\.cache\pip 2>nul

set PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
if not exist "%PY%" (
  echo 未找到 Python 3.11: %PY%
  exit /b 1
)

if not exist "D:\AI-test\.venv\Scripts\python.exe" (
  echo 创建虚拟环境 D:\AI-test\.venv ...
  "%PY%" -m venv "D:\AI-test\.venv"
)

echo 安装依赖...
"D:\AI-test\.venv\Scripts\python.exe" -m pip install --upgrade pip --cache-dir D:\AI-test\.cache\pip
"D:\AI-test\.venv\Scripts\python.exe" -m pip install --cache-dir D:\AI-test\.cache\pip -e D:\AI-test\packages\contracts
"D:\AI-test\.venv\Scripts\python.exe" -m pip install --cache-dir D:\AI-test\.cache\pip -r D:\AI-test\engine\requirements.txt
"D:\AI-test\.venv\Scripts\python.exe" -m pip install --cache-dir D:\AI-test\.cache\pip -r D:\AI-test\gateway\requirements.txt

"D:\AI-test\.venv\Scripts\python.exe" -c "import fastapi,langgraph,sqlalchemy,ai_test_contracts; print('venv OK')"
echo.
echo 完成。可运行 CLEAN-C-AND-SETUP.cmd 一键启动，或分别执行 start-*.ps1
pause
