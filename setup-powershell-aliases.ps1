# Настройка PowerShell алиасов для быстрого деплоя
# Запустите один раз: .\setup-powershell-aliases.ps1
# Или добавьте содержимое в ваш PowerShell профиль

$profilePath = $PROFILE

# Создаем профиль если его нет
if (-not (Test-Path $profilePath)) {
    New-Item -Path $profilePath -ItemType File -Force | Out-Null
    Write-Host "[INFO] PowerShell profile created: $profilePath" -ForegroundColor Green
}

# Определяем путь к проекту автоматически
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Добавляем функции в профиль
$aliasesContent = @"

# Secure Content Service - Quick Deploy Aliases
# Project path: $ProjectPath

function Update-File {
    param([Parameter(Mandatory=`$true)][string]`$FilePath)
    & "$ProjectPath\quick-update.ps1" -FilePath `$FilePath
}

function Quick-Update {
    param([string]`$FilePath = "")
    if (`$FilePath) {
        & "$ProjectPath\quick-update.ps1" -FilePath `$FilePath
    } else {
        & "$ProjectPath\quick-update.ps1"
    }
}

function Restart-Backend {
    ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose restart backend"
}

function Deploy-All {
    & "$ProjectPath\deploy.ps1"
}

function Connect-VPS {
    ssh root@89.110.111.184
}

function Show-Logs {
    ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose logs -f backend"
}

# Алиасы для быстрого доступа
Set-Alias -Name update -Value Update-File
Set-Alias -Name qupdate -Value Quick-Update
Set-Alias -Name restart -Value Restart-Backend
Set-Alias -Name deploy -Value Deploy-All
Set-Alias -Name vps -Value Connect-VPS
Set-Alias -Name logs -Value Show-Logs

"@

# Проверяем, не добавлены ли уже алиасы
$currentProfile = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
if ($currentProfile -notlike "*Secure Content Service*") {
    Add-Content -Path $profilePath -Value $aliasesContent
    Write-Host "[INFO] Aliases added to PowerShell profile" -ForegroundColor Green
    Write-Host ""
    Write-Host "Available commands:" -ForegroundColor Cyan
    Write-Host "  update backend\app\api\viewer.py  - Update single file and restart" -ForegroundColor Yellow
    Write-Host "  qupdate                           - Update all files and restart" -ForegroundColor Yellow
    Write-Host "  qupdate file.py                   - Update specific file and restart" -ForegroundColor Yellow
    Write-Host "  restart                           - Restart backend only" -ForegroundColor Yellow
    Write-Host "  deploy                            - Full deployment (rebuild)" -ForegroundColor Yellow
    Write-Host "  vps                               - Connect to VPS" -ForegroundColor Yellow
    Write-Host "  logs                              - Show backend logs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[INFO] Reload PowerShell or run: . `$PROFILE" -ForegroundColor Green
} else {
    Write-Host "[INFO] Aliases already exist in profile" -ForegroundColor Yellow
}
