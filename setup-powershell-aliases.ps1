# Настройка PowerShell алиасов для быстрого деплоя
# Запустите один раз: .\setup-powershell-aliases.ps1
# Или добавьте содержимое в ваш PowerShell профиль

$profilePath = $PROFILE

# Создаем профиль если его нет
if (-not (Test-Path $profilePath)) {
    New-Item -Path $profilePath -ItemType File -Force | Out-Null
    Write-Host "[INFO] PowerShell profile created: $profilePath" -ForegroundColor Green
}

# Добавляем функции в профиль
$aliasesContent = @"

# Secure Content Service - Quick Deploy Aliases
function Update-File {
    param([Parameter(Mandatory=`$true)][string]`$FilePath)
    & "D:\WORK\secure-content-service\deploy-single-file.ps1" `$FilePath
}

function Restart-Backend {
    ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose restart backend"
}

function Deploy-All {
    & "D:\WORK\secure-content-service\deploy.ps1"
}

function Connect-VPS {
    ssh root@89.110.111.184
}

function Show-Logs {
    ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose logs -f backend"
}

# Алиасы для быстрого доступа
Set-Alias -Name update -Value Update-File
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
    Write-Host "  update backend\app\api\viewer.py  - Update single file" -ForegroundColor Yellow
    Write-Host "  restart                          - Restart backend" -ForegroundColor Yellow
    Write-Host "  deploy                           - Full deployment" -ForegroundColor Yellow
    Write-Host "  vps                              - Connect to VPS" -ForegroundColor Yellow
    Write-Host "  logs                             - Show backend logs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[INFO] Reload PowerShell or run: . `$PROFILE" -ForegroundColor Green
} else {
    Write-Host "[INFO] Aliases already exist in profile" -ForegroundColor Yellow
}
