@echo off
REM Полный деплой проекта на VPS

echo Deploying to VPS...
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1"
pause
