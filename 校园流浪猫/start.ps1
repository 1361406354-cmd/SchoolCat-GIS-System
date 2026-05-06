# 校猫守护 - 校园流浪猫管理平台 启动脚本 (PowerShell)
$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir "backend"

Write-Host "校猫守护 - 校园流浪猫管理平台" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "[OK] Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/"
    Read-Host "按 Enter 退出"
    exit 1
}

# Install dependencies
Set-Location $backendDir
Write-Host "[..] 正在安装依赖..." -ForegroundColor Yellow
pip install -r requirements.txt 2>&1 | Out-Null
Write-Host "[OK] 依赖安装完成" -ForegroundColor Green

# Initialize DB
Write-Host "[..] 正在初始化数据库..." -ForegroundColor Yellow
python -c "from app import app, db; app.app_context().push(); db.create_all()"
Write-Host "[OK] 数据库初始化完成" -ForegroundColor Green

# Kill existing process on port 5000
$existing = netstat -ano | Select-String ":5000 "
if ($existing) {
    Write-Host "[警告] 端口 5000 已被占用，正在关闭旧进程..." -ForegroundColor Yellow
    $existing | ForEach-Object {
        $pid = $_ -replace '.*\s+(\d+)\s*$', '$1'
        if ($pid -ne $pid -and $pid -gt 0) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
    }
    Start-Sleep 2
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 服务启动中..." -ForegroundColor Cyan
Write-Host " 浏览器访问: http://localhost:5000" -ForegroundColor White
Write-Host " 管理员账号: admin / admin123" -ForegroundColor White
Write-Host " 志愿者账号: volunteer / vol123" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Start-Process "http://localhost:5000"
python app.py

Read-Host "按 Enter 退出"
