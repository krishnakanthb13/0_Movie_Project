@echo off
title Movie Library - Environment Setup
color 0B

echo.
echo  ========================================
echo   SETTING UP UV VIRTUAL ENVIRONMENT
echo  ========================================
echo.

:: Check for uv
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] 'uv' is not installed or not in PATH.
    echo Please install it first: https://github.com/astral-sh/uv
    pause
    exit /b 1
)

echo [+] UV found. Creating/Syncing virtual environment...
echo.

:: Create .venv and install dependencies from requirements.txt
:: uv sync is often better if we have a pyproject.toml, but uv pip install works great for requirements.txt
uv venv
uv pip install -r requirements.txt

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Error during environment setup.
    pause
    exit /b 1
)

echo.
echo  ========================================
echo   SETUP COMPLETE!
echo  ========================================
echo.
echo  You can now run MovieLibrary.bat safely.
pause
