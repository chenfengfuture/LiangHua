@echo off
chcp 65001 > nul
title 量华量化平台
echo ════════════════════════════════════════
echo     量华量化平台 - Starting...
echo ════════════════════════════════════════

REM 获取脚本所在目录（项目根目录）
set "PROJECT_ROOT=%~dp0"
echo 项目路径: %PROJECT_ROOT%

REM 使用管理版 Python 3.13.12（已预装所有依赖）
set "MANAGED_PYTHON=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"

REM 检查 Python 是否可用
%MANAGED_PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到管理版 Python
    pause
    exit /b 1
)
%MANAGED_PYTHON% --version 2>&1

REM 检查 Node.js 是否可用
node --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Node.js 或 Node.js 未添加到 PATH
    pause
    exit /b 1
)

REM ───────────────────────────────────────────
REM  端口清理（PowerShell 脚本，无转义问题）
REM ───────────────────────────────────────────
echo.
echo 检查并释放端口...
powershell -ExecutionPolicy Bypass -File "%PROJECT_ROOT%scripts\cleanup_ports.ps1"
if errorlevel 1 (
    echo 警告: 端口清理脚本执行异常，继续启动...
)

REM ───────────────────────────────────────────
REM  启动后端和前端
REM ───────────────────────────────────────────
echo.
echo [1/2] 启动后端 API (端口 8001)...
cd /d "%PROJECT_ROOT%backend"
start /B "" "%MANAGED_PYTHON%" main.py

cd /d "%PROJECT_ROOT%frontend"
timeout /t 3 /nobreak > nul
echo [2/2] 启动前端开发服务器 (端口 3000)...
start /B "" node node_modules\vite\bin\vite.js --port 3000

cd /d "%PROJECT_ROOT%"

echo.
echo ════════════════════════════════════════
echo  服务已启动（运行在同一窗口下）
echo   前端........ http://localhost:3000
echo   后端 API.... http://localhost:8001
echo   API 文档.... http://localhost:8001/docs
echo ════════════════════════════════════════
echo.
echo  关闭此窗口 或 按任意键 → 自动停止所有服务并退出
echo.

REM 等待用户按键或关闭窗口
pause > nul

REM ── 用户按了任意键，执行清理 ──
echo.
echo 正在停止所有服务...
powershell -ExecutionPolicy Bypass -File "%PROJECT_ROOT%scripts\cleanup_ports.ps1"

echo ✓ 量华平台已停止
timeout /t 2 /nobreak > nul
