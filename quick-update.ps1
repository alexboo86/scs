# Быстрое обновление файлов на VPS без пересборки контейнера
# Использование: .\quick-update.ps1 [путь_к_файлу]
# Пример: .\quick-update.ps1 backend\app\api\viewer.py
# Или без параметров - обновит все измененные файлы

param(
    [string]$FilePath = "",
    [string]$VPS_IP = "89.110.111.184",
    [string]$VPS_USER = "root",
    [string]$PROJECT_DIR = "secure-content-service",
    [switch]$NoRestart = $false
)

$ErrorActionPreference = "Stop"

# Определяем путь к проекту автоматически (откуда запущен скрипт)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_PATH = $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Quick Update to VPS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Функция для выполнения SSH команд (использует SSH ключи если настроены)
function Invoke-SSHCommand {
    param([string]$Command)
    
    # Используем BatchMode для автоматического использования SSH ключей
    ssh -o BatchMode=yes "${VPS_USER}@${VPS_IP}" $Command
}

# Функция для копирования файла
function Copy-FileToVPS {
    param([string]$LocalPath, [string]$RemotePath)
    
    Write-Host "  → $LocalPath" -ForegroundColor Yellow
    
    # Создаем директорию на VPS если нужно
    $RemoteDir = Split-Path $RemotePath -Parent
    Invoke-SSHCommand "mkdir -p `"$RemoteDir`"" | Out-Null
    
    # Копируем файл используя SFTP
    $localPathFixed = $LocalPath -replace '\\', '/'
    
    # Expand ~ to absolute path for SFTP
    $RemotePathExpanded = $RemotePath -replace '^~/', '/root/'
    $RemoteDir = Split-Path $RemotePathExpanded -Parent
    $RemoteFileName = Split-Path $RemotePathExpanded -Leaf
    
    # Create directory if needed (using SSH, SFTP mkdir doesn't support -p)
    Invoke-SSHCommand "mkdir -p `"$RemoteDir`"" | Out-Null
    
    # Create SFTP batch script
    $sftpScript = [System.IO.Path]::GetTempFileName()
    $sftpCommands = @"
cd `"$RemoteDir`"
put `"$localPathFixed`" `"$RemoteFileName`"
quit
"@
    
    $sftpCommands | Out-File -FilePath $sftpScript -Encoding ASCII -NoNewline
    
    try {
        # Use SFTP with timeout via Job
        $sftpJob = Start-Job -ScriptBlock {
            param($script, $user, $ip)
            & sftp -b $script "${user}@${ip}" 2>&1
        } -ArgumentList $sftpScript, $VPS_USER, $VPS_IP
        
        # Wait for job with timeout (30 seconds)
        $completedJob = $sftpJob | Wait-Job -Timeout 30
        
        if ($completedJob) {
            # Job completed
            Receive-Job $sftpJob | Out-Null
            Remove-Job $sftpJob -Force
        } else {
            # Timeout - job still running
            Stop-Job $sftpJob -ErrorAction SilentlyContinue
            Remove-Job $sftpJob -Force -ErrorAction SilentlyContinue
            Write-Host "    [WARN] SFTP timed out" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    [ERROR] SFTP failed: $_" -ForegroundColor Red
    } finally {
        if (Test-Path $sftpScript) {
            Remove-Item $sftpScript -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($FilePath) {
    # Обновляем один файл
    $FullPath = Join-Path $PROJECT_PATH $FilePath
    
    if (-not (Test-Path $FullPath)) {
        Write-Host "[ERROR] File not found: $FullPath" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "[INFO] Updating single file..." -ForegroundColor Green
    $VPSPath = "~/projects/${PROJECT_DIR}/${FilePath}"
    Copy-FileToVPS -LocalPath $FullPath -RemotePath $VPSPath
    
} else {
    # Обновляем все основные файлы проекта
    Write-Host "[INFO] Updating project files..." -ForegroundColor Green
    
    # Список директорий и файлов для обновления
    $itemsToUpdate = @(
        "backend\app",
        "frontend\templates",
        "docker-compose.yml",
        "nginx.conf"
    )
    
    foreach ($item in $itemsToUpdate) {
        $LocalItem = Join-Path $PROJECT_PATH $item
        
        if (Test-Path $LocalItem) {
            if (Test-Path $LocalItem -PathType Container) {
                # Это директория - копируем все файлы
                Write-Host "[INFO] Syncing directory: $item" -ForegroundColor Cyan
                
                # Используем scp для рекурсивного копирования
                $VPSItem = "~/projects/${PROJECT_DIR}/${item}"
                
                if (Get-Command pscp -ErrorAction SilentlyContinue) {
                    # pscp рекурсивно
                    Get-ChildItem -Path $LocalItem -Recurse -File | ForEach-Object {
                        $relativePath = $_.FullName.Substring($PROJECT_PATH.Length + 1)
                        $vpsFilePath = "~/projects/${PROJECT_DIR}/${relativePath}"
                        Copy-FileToVPS -LocalPath $_.FullName -RemotePath $vpsFilePath
                    }
                } else {
                    # scp рекурсивно
                    scp -r "`"$LocalItem\*`" ${VPS_USER}@${VPS_IP}:`"$VPSItem`"" 2>&1 | Out-Null
                }
            } else {
                # Это файл
                Write-Host "[INFO] Copying file: $item" -ForegroundColor Cyan
                $VPSItem = "~/projects/${PROJECT_DIR}/${item}"
                Copy-FileToVPS -LocalPath $LocalItem -RemotePath $VPSItem
            }
        }
    }
}

Write-Host ""
Write-Host "[INFO] Files updated successfully!" -ForegroundColor Green

# Перезапускаем backend если нужно
if (-not $NoRestart) {
    Write-Host ""
    Write-Host "[INFO] Restarting backend..." -ForegroundColor Green
    Invoke-SSHCommand "cd ~/projects/${PROJECT_DIR} && docker-compose restart backend"
    Write-Host "[INFO] Backend restarted!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[INFO] Skipping restart (use -NoRestart to skip)" -ForegroundColor Yellow
    Write-Host "[INFO] Note: With volume mount and --reload, changes may apply automatically" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Update Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
