# 启动量华量化平台
Write-Host "启动量华量化平台..." -ForegroundColor Green

# 获取脚本所在目录（项目根目录）
$PROJECT_ROOT = $PSScriptRoot
Write-Host "项目路径: $PROJECT_ROOT" -ForegroundColor Gray

# 检查 Python 是否可用
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python 版本: $pythonVersion" -ForegroundColor Gray
} catch {
    Write-Host "错误: 未找到 Python 或 Python 未添加到 PATH" -ForegroundColor Red
    Write-Host "请确保已安装 Python 3.x 并添加到系统环境变量" -ForegroundColor Yellow
    pause
    exit 1
}

# 检查 Node.js 是否可用
try {
    $nodeVersion = node --version 2>&1
    Write-Host "Node.js 版本: $nodeVersion" -ForegroundColor Gray
} catch {
    Write-Host "错误: 未找到 Node.js 或 Node.js 未添加到 PATH" -ForegroundColor Red
    Write-Host "请确保已安装 Node.js 并添加到系统环境变量" -ForegroundColor Yellow
    pause
    exit 1
}

# [1/2] 启动后端 API (端口 8001)
Write-Host "[1/2] 启动后端 API (端口 8001)..." -ForegroundColor Cyan
$backendJob = Start-Job -ScriptBlock {
    Set-Location "$using:PROJECT_ROOT\backend"
    python main.py
}

Start-Sleep -Seconds 2

# [2/2] 启动前端开发服务器 (端口 3000)
Write-Host "[2/2] 启动前端开发服务器 (端口 3000)..." -ForegroundColor Cyan
$frontendJob = Start-Job -ScriptBlock {
    Set-Location "$using:PROJECT_ROOT\frontend"
    node node_modules\vite\bin\vite.js --port 3000
}

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "服务已启动:" -ForegroundColor Green
Write-Host "  前端: http://localhost:3000" -ForegroundColor Yellow
Write-Host "  后端 API: http://localhost:8001" -ForegroundColor Yellow
Write-Host "  API 文档: http://localhost:8001/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "提示: 关闭此窗口不会停止服务，请使用 停止量华平台.bat 停止服务" -ForegroundColor Gray

# 打开浏览器
Start-Process "http://localhost:3000"

# 保持窗口打开，显示日志
Write-Host ""
Write-Host "按 Ctrl+C 停止查看日志（服务仍在后台运行）" -ForegroundColor Gray
Write-Host ""

while ($true) {
    Receive-Job -Job $backendJob -Keep | ForEach-Object { Write-Host "[后端] $_" -ForegroundColor DarkGray }
    Receive-Job -Job $frontendJob -Keep | ForEach-Object { Write-Host "[前端] $_" -ForegroundColor DarkGray }
    Start-Sleep -Milliseconds 500
}
