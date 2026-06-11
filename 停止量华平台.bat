@echo off
chcp 65001 > nul
echo 正在停止量华量化平台...
echo.

echo [1/2] 停止后端 API (端口 8001)...
echo [2/2] 停止前端开发服务器 (端口 3000)...

powershell -ExecutionPolicy Bypass -File "%~dp0scripts\cleanup_ports.ps1"

echo.
echo ✓ 量华平台已停止
echo.
pause
