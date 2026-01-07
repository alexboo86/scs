# Быстрый деплой на VPS (PowerShell версия для Windows)
# Использование: .\deploy.ps1 [VPS_IP] [VPS_USER]
# Пример: .\deploy.ps1 89.110.111.184 root

param(
    [string]$VPS_IP = "89.110.111.184",
    [string]$VPS_USER = "root",
    [string]$PROJECT_DIR = "secure-content-service",
    [string]$VPS_PASSWORD = "vE1x~!56#8nF36p8dLGW"
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

# Функция для выполнения SSH команд
function Invoke-SSHCommand {
    param([string]$Command)
    
    # Пробуем использовать plink (PuTTY) для автоматического ввода пароля
    if (Get-Command plink -ErrorAction SilentlyContinue) {
        $plinkCmd = "echo y | plink -ssh -pw `"$VPS_PASSWORD`" ${VPS_USER}@${VPS_IP} `"$Command`""
        Invoke-Expression $plinkCmd
    } else {
        # Используем обычный ssh (потребует ввода пароля вручную или SSH ключи)
        ssh "${VPS_USER}@${VPS_IP}" $Command
    }
}

# Проверка подключения
Write-Step "Checking VPS connection..."
try {
    $testResult = Invoke-SSHCommand "echo 'Connected'"
    if ($LASTEXITCODE -eq 0 -or $testResult) {
        Write-Info "Connection established"
    } else {
        Write-Error "Failed to connect to VPS. Check IP address and SSH access."
        exit 1
    }
} catch {
    Write-Error "Failed to connect to VPS. Check IP address and SSH access."
    Write-Info "Tip: Setup SSH keys using: .\setup-ssh-keys.ps1"
    exit 1
}

# Определяем путь к проекту автоматически (откуда запущен скрипт)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_PATH = $ScriptDir

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

Invoke-SSHCommand $commands

Write-Info "Done! Project updated on VPS"
