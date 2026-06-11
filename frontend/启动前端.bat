@echo off
chcp 65001 > nul
title 量华量化平台 - 前端启动

echo ========================================
echo    量华量化平台 - 前端服务启动中
echo ========================================
echo.

REM 获取当前批处理文件所在目录
set "PROJECT_DIR=%~dp0"

REM 切换到项目目录
cd /d "%PROJECT_DIR%"

echo 项目目录: %PROJECT_DIR%
echo.

REM 检查 node_modules 是否存在
if not exist "node_modules" (
    echo [警告] 未检测到 node_modules，正在安装依赖...
    call npm install
    if errorlevel 1 (
        echo [错误] 依赖安装失败！
        pause
        exit /b 1
    )
)

echo [信息] 正在启动开发服务器...
echo [信息] 启动后请访问: http://localhost:3000
echo.

REM 启动开发服务器
call npm run dev

if errorlevel 1 (
    echo.
    echo [错误] 启动失败！
    pause
)
