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
Write-Step "Checking VPS connection..."
try {
    $null = ssh -o ConnectTimeout=5 "${VPS_USER}@${VPS_IP}" "echo 'Connected'" 2>&1
    Write-Info "Connection established"
} catch {
    Write-Error "Failed to connect to VPS. Check IP address and SSH access."
    exit 1
}

# Путь к проекту
$PROJECT_PATH = "D:\WORK\secure-content-service"

# Проверка существования пути
if (-not (Test-Path $PROJECT_PATH)) {
    Write-Error "Project path not found: $PROJECT_PATH"
    exit 1
}

Write-Step "Syncing files to VPS..."

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
        Write-Host "  Copying: $dir"
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
        Write-Host "  Copying: $file"
        scp $source "${VPS_USER}@${VPS_IP}:~/projects/${PROJECT_DIR}/"
    }
}

Write-Info "Files copied to VPS"

# Выполняем команды на VPS
Write-Step "Rebuilding and restarting container..."

$commands = @"
cd ~/projects/${PROJECT_DIR}
echo 'Building backend container...'
docker-compose build backend
echo 'Restarting backend...'
docker-compose restart backend
echo ''
echo 'Container status:'
docker-compose ps
echo ''
echo 'Deployment complete!'
"@

ssh "${VPS_USER}@${VPS_IP}" $commands

Write-Info "Done! Project updated on VPS"
