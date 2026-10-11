@echo off
chcp 65001 >nul
echo 清理 C 盘 Temp / npm / pip 缓存...
set TEMP=D:\AI-test\.cache\tmp
set TMP=D:\AI-test\.cache\tmp
mkdir D:\AI-test\.cache\tmp 2>nul

del /q /f /s "%LOCALAPPDATA%\Temp\*.*" >nul 2>nul
for /d %%i in ("%LOCALAPPDATA%\Temp\*") do rd /s /q "%%i" >nul 2>nul
if exist "%LOCALAPPDATA%\npm-cache" rd /s /q "%LOCALAPPDATA%\npm-cache" >nul 2>nul
if exist "%LOCALAPPDATA%\pip\Cache" rd /s /q "%LOCALAPPDATA%\pip\Cache" >nul 2>nul

echo 当前 C 盘空间:
fsutil volume diskfree C:
echo.
echo 若仍不足 1GB，请手动清理：回收站、Windows 临时文件、大型安装包。
pause
