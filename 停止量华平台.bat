@echo off
echo 正在停止量华量化平台...
echo.

:: 停止后端 Python 进程 (端口 8001)
echo [1/2] 停止后端 API (端口 8001)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001') do (
    echo   找到进程 PID: %%a，正在终止...
    taskkill /F /PID %%a 2>nul
)

:: 停止前端 Node 进程 (端口 3000)
echo [2/2] 停止前端开发服务器 (端口 3000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo   找到进程 PID: %%a，正在终止...
    taskkill /F /PID %%a 2>nul
)

echo.
echo ✓ 量华平台已停止
echo.
pause
