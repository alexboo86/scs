@echo off
REM Setup SSH keys for passwordless access
REM Usage: setup-ssh-keys.bat

powershell -ExecutionPolicy Bypass -File "%~dp0setup-ssh-keys.ps1" %*
