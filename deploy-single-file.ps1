# Быстрый деплой одного файла на VPS (PowerShell)
# Использование: .\deploy-single-file.ps1 <путь_к_файлу>
# Пример: .\deploy-single-file.ps1 backend\app\api\viewer.py

param(
    [Parameter(Mandatory=$true)]
    [string]$FilePath,
    [string]$VPS_IP = "89.110.111.184",
    [string]$VPS_USER = "root",
    [string]$PROJECT_DIR = "secure-content-service"
)

$ErrorActionPreference = "Stop"

$PROJECT_PATH = "D:\WORK\secure-content-service"
$FullPath = Join-Path $PROJECT_PATH $FilePath

if (-not (Test-Path $FullPath)) {
    Write-Host "[ERROR] Файл не найден: $FullPath" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Копирование файла: $FilePath" -ForegroundColor Green

# Определяем путь на VPS (сохраняем структуру директорий)
$VPSPath = "~/projects/${PROJECT_DIR}/${FilePath}"

# Создаем директорию на VPS если нужно
$VPSDir = Split-Path $VPSPath -Parent
ssh "${VPS_USER}@${VPS_IP}" "mkdir -p $VPSDir" | Out-Null

# Копируем файл
scp $FullPath "${VPS_USER}@${VPS_IP}:${VPSPath}"

Write-Host "[INFO] Перезапуск backend..." -ForegroundColor Green
ssh "${VPS_USER}@${VPS_IP}" "cd ~/projects/${PROJECT_DIR} && docker-compose restart backend"

Write-Host "[INFO] ✅ Готово! Файл обновлен и сервис перезапущен" -ForegroundColor Green
