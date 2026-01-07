# Обновить файл и перезапустить backend
# Использование: .\update-and-restart.ps1 backend\app\api\viewer.py

param(
    [Parameter(Mandatory=$true)]
    [string]$FilePath
)

& "$PSScriptRoot\quick-update.ps1" -FilePath $FilePath
