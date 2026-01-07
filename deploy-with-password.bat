@echo off
REM Деплой с ручным вводом пароля
REM Использование: deploy-with-password.bat

powershell -ExecutionPolicy Bypass -File "%~dp0deploy-with-password.ps1" %*
