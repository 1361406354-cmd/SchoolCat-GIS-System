@echo off
chcp 65001 >nul
title 校猫守护 - 校园流浪猫管理平台
cd /d "%~dp0backend"

echo ============================================
echo   校猫守护 - 校园流浪猫管理平台
echo ============================================
echo.

REM Try to find Python in common locations if not in PATH
set PYTHON_CMD=python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where python3 >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python3
    ) else (
        REM Check common install paths
        for %%p in (
            "D:\Python\Python313\python.exe"
            "C:\Python313\python.exe"
            "C:\Python3\python.exe"
            "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
            "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
            "%ProgramFiles%\Python313\python.exe"
        ) do (
            if exist %%p (
                set PYTHON_CMD=%%~p
                goto :found_python
            )
        )
        echo [错误] 未找到 Python，请先安装 Python 3
        echo 下载地址: https://www.python.org/downloads/
        echo.
        echo 安装时请勾选 "Add Python to PATH"
        pause
        exit /b 1
    )
)
:found_python

echo [OK] Python 路径: %PYTHON_CMD%
%PYTHON_CMD% --version

echo.
REM Install dependencies
echo [..] 正在安装依赖...
%PYTHON_CMD% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖安装完成

echo.
REM Initialize database
echo [..] 正在初始化数据库...
%PYTHON_CMD% -c "from app import app, db; app.app_context().push(); db.create_all()"
if %errorlevel% neq 0 (
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)
echo [OK] 数据库初始化完成

echo.
REM Check if port is in use
netstat -ano | find ":5000 " >nul 2>nul
if %errorlevel% equ 0 (
    echo [警告] 端口 5000 已被占用，正在关闭旧进程...
    for /f "tokens=5" %%a in ('netstat -ano ^| find ":5000 "') do (
        taskkill /f /pid %%a >nul 2>nul
    )
    timeout /t 2 /nobreak >nul
)

echo.
echo ============================================
echo  服务启动中...
echo  浏览器自动打开: http://localhost:5000
echo  管理员账号: admin / admin123
echo  志愿者账号: volunteer / vol123
echo ============================================
echo.

start http://localhost:5000
%PYTHON_CMD% app.py

echo.
echo 服务已停止。
pause
