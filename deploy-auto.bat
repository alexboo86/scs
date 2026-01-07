@echo off
REM Automatic deploy without password
REM Usage: deploy-auto.bat

powershell -ExecutionPolicy Bypass -File "%~dp0deploy-auto.ps1" %*
