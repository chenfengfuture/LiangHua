@echo off
chcp 65001 > nul
echo 启动量华量化平台...

REM 获取脚本所在目录（项目根目录）
set "PROJECT_ROOT=%~dp0"
echo 项目路径: %PROJECT_ROOT%

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python 或 Python 未添加到 PATH
    echo 请确保已安装 Python 3.x 并添加到系统环境变量
    pause
    exit /b 1
)

REM 检查 Node.js 是否可用
node --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Node.js 或 Node.js 未添加到 PATH
    echo 请确保已安装 Node.js 并添加到系统环境变量
    pause
    exit /b 1
)

echo [1/2] 启动后端 API (端口 8001)...
start "量华-后端" cmd /k "cd /d "%PROJECT_ROOT%backend" && python main.py"

timeout /t 3 /nobreak > nul

echo [2/2] 启动前端开发服务器 (端口 3000)...
start "量华-前端" cmd /k "cd /d "%PROJECT_ROOT%frontend" && node node_modules\vite\bin\vite.js --port 3000"

timeout /t 5 /nobreak > nul

echo.
echo 服务已启动:
echo   前端: http://localhost:3000
echo   后端 API: http://localhost:8001
echo   API 文档: http://localhost:8001/docs
echo.
echo 提示: 请不要关闭后端/前端的命令行窗口，关闭窗口会停止对应服务
echo 提示: 如需停止服务，请使用 停止量华平台.bat
echo.
echo 浏览器将在5秒后自动打开前端页面...
timeout /t 5 /nobreak > nul

REM 只打开一次前端页面
start "" "http://localhost:3000"
