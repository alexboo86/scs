@echo off
REM Быстрое обновление файлов на VPS
REM Использование: quick-update.bat [путь_к_файлу]
REM Пример: quick-update.bat backend\app\api\viewer.py

powershell -ExecutionPolicy Bypass -File "%~dp0quick-update.ps1" %*
