# Быстрый деплой одного файла на VPS (PowerShell)
# Использование: .\deploy-single-file.ps1 <путь_к_файлу>
# Пример: .\deploy-single-file.ps1 backend\app\api\viewer.py

param(
    [Parameter(Mandatory=$true)]
    [string]$FilePath,
    [string]$VPS_IP = "89.110.111.184",
    [string]$VPS_USER = "root",
    [string]$PROJECT_DIR = "secure-content-service",
    [string]$VPS_PASSWORD = "vE1x~!56#8nF36p8dLGW"
)

$ErrorActionPreference = "Stop"

# Определяем путь к проекту автоматически (откуда запущен скрипт)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_PATH = $ScriptDir
$FullPath = Join-Path $PROJECT_PATH $FilePath

if (-not (Test-Path $FullPath)) {
    Write-Host "[ERROR] File not found: $FullPath" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Copying file: $FilePath" -ForegroundColor Green

# Определяем путь на VPS (сохраняем структуру директорий)
$VPSPath = "~/projects/${PROJECT_DIR}/${FilePath}"

# Функция для выполнения SSH команд с паролем
function Invoke-SSHCommand {
    param([string]$Command)
    if (Get-Command plink -ErrorAction SilentlyContinue) {
        $plinkCmd = "echo y | plink -ssh -pw `"$VPS_PASSWORD`" ${VPS_USER}@${VPS_IP} `"$Command`""
        Invoke-Expression $plinkCmd
    } else {
        ssh "${VPS_USER}@${VPS_IP}" $Command
    }
}

# Создаем директорию на VPS если нужно
$VPSDir = Split-Path $VPSPath -Parent
Invoke-SSHCommand "mkdir -p $VPSDir" | Out-Null

# Копируем файл (scp с паролем через plink)
if (Get-Command pscp -ErrorAction SilentlyContinue) {
    $pscpCmd = "echo y | pscp -pw `"$VPS_PASSWORD`" `"$FullPath`" ${VPS_USER}@${VPS_IP}:${VPSPath}"
    Invoke-Expression $pscpCmd
} else {
    scp $FullPath "${VPS_USER}@${VPS_IP}:${VPSPath}"
}

Write-Host "[INFO] Restarting backend..." -ForegroundColor Green
Invoke-SSHCommand "cd ~/projects/${PROJECT_DIR} && docker-compose restart backend"

Write-Host "[INFO] Done! File updated and service restarted" -ForegroundColor Green
