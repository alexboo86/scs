@echo off
REM Python deploy script wrapper
REM Usage: deploy.bat

python deploy.py

if errorlevel 1 (
    echo.
    echo [ERROR] Deployment failed!
    echo [INFO] Make sure Python and paramiko are installed:
    echo   pip install -r requirements-deploy.txt
    pause
    exit /b 1
)
