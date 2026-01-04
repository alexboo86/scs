@echo off
REM Быстрое обновление файла на VPS
REM Использование: update-file.bat backend\app\api\viewer.py

if "%~1"=="" (
    echo Usage: update-file.bat ^<file_path^>
    echo Example: update-file.bat backend\app\api\viewer.py
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File "%~dp0deploy-single-file.ps1" "%~1"
