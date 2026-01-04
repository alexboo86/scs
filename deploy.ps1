# Быстрый деплой на VPS (PowerShell версия для Windows)
# Использование: .\deploy.ps1 [VPS_IP] [VPS_USER]
# Пример: .\deploy.ps1 89.110.111.184 root

param(
    [string]$VPS_IP = "89.110.111.184",
    [string]$VPS_USER = "root",
    [string]$PROJECT_DIR = "secure-content-service"
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Blue
}

# Проверка подключения
Write-Step "Проверка подключения к VPS..."
try {
    $null = ssh -o ConnectTimeout=5 "${VPS_USER}@${VPS_IP}" "echo 'Connected'" 2>&1
    Write-Info "Подключение установлено"
} catch {
    Write-Error "Не удалось подключиться к VPS. Проверьте IP адрес и SSH доступ."
    exit 1
}

# Путь к проекту
$PROJECT_PATH = "D:\WORK\secure-content-service"

# Проверка существования пути
if (-not (Test-Path $PROJECT_PATH)) {
    Write-Error "Путь к проекту не найден: $PROJECT_PATH"
    exit 1
}

Write-Step "Синхронизация файлов на VPS..."

# Используем scp для копирования (rsync может быть недоступен в Windows)
# Копируем основные директории
$directories = @(
    "backend",
    "frontend",
    "docker-compose.yml",
    "Dockerfile",
    "requirements.txt"
)

foreach ($dir in $directories) {
    $source = Join-Path $PROJECT_PATH $dir
    if (Test-Path $source) {
        Write-Host "  Копирование: $dir"
        if (Test-Path $source -PathType Container) {
            scp -r "${source}\*" "${VPS_USER}@${VPS_IP}:~/projects/${PROJECT_DIR}/${dir}/"
        } else {
            scp $source "${VPS_USER}@${VPS_IP}:~/projects/${PROJECT_DIR}/"
        }
    }
}

# Копируем отдельные файлы
$files = @(
    ".dockerignore",
    "env.example",
    "nginx.conf"
)

foreach ($file in $files) {
    $source = Join-Path $PROJECT_PATH $file
    if (Test-Path $source) {
        Write-Host "  Копирование: $file"
        scp $source "${VPS_USER}@${VPS_IP}:~/projects/${PROJECT_DIR}/"
    }
}

Write-Info "Файлы скопированы на VPS"

# Выполняем команды на VPS
Write-Step "Пересборка и перезапуск контейнера..."

$commands = @"
cd ~/projects/${PROJECT_DIR}
echo 'Сборка backend контейнера...'
docker-compose build backend
echo 'Перезапуск backend...'
docker-compose restart backend
echo ''
echo 'Статус контейнеров:'
docker-compose ps
echo ''
echo 'Деплой завершен!'
"@

ssh "${VPS_USER}@${VPS_IP}" $commands

Write-Info "Готово! Проект обновлен на VPS"
