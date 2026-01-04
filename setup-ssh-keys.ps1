# Настройка SSH ключей для автоматического входа на VPS
# Использование: .\setup-ssh-keys.ps1

param(
    [string]$VPS_IP = "89.110.111.184",
    [string]$VPS_USER = "root"
)

$ErrorActionPreference = "Stop"

Write-Host "[INFO] Setting up SSH keys for automatic login..." -ForegroundColor Green

# Проверяем наличие SSH ключа
$sshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519"
$sshPubKeyPath = "$env:USERPROFILE\.ssh\id_ed25519.pub"

if (-not (Test-Path $sshKeyPath)) {
    Write-Host "[INFO] Generating SSH key..." -ForegroundColor Yellow
    ssh-keygen -t ed25519 -C "vps-access" -f $sshKeyPath -N '""'
    Write-Host "[INFO] SSH key generated" -ForegroundColor Green
} else {
    Write-Host "[INFO] SSH key already exists" -ForegroundColor Green
}

# Читаем публичный ключ
$publicKey = Get-Content $sshPubKeyPath -Raw

Write-Host "[INFO] Copying public key to VPS..." -ForegroundColor Yellow
Write-Host "[INFO] You will be asked for the root password: vE1x~!56#8nF36p8dLGW" -ForegroundColor Cyan

# Копируем ключ на VPS
$tempScript = [System.IO.Path]::GetTempFileName()
$scriptContent = @"
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo '$publicKey' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo 'SSH key added successfully'
"@

$scriptContent | Out-File -FilePath $tempScript -Encoding ASCII

# Используем ssh с паролем через expect или просто копируем ключ
Write-Host "[INFO] Please enter password when prompted: vE1x~!56#8nF36p8dLGW" -ForegroundColor Cyan

# Пробуем использовать ssh-copy-id (если доступен)
if (Get-Command ssh-copy-id -ErrorAction SilentlyContinue) {
    ssh-copy-id "${VPS_USER}@${VPS_IP}"
} else {
    # Альтернативный способ - вручную
    Write-Host "[INFO] Manual setup required:" -ForegroundColor Yellow
    Write-Host "1. Copy this public key:" -ForegroundColor Yellow
    Write-Host $publicKey -ForegroundColor Cyan
    Write-Host ""
    Write-Host "2. Run on VPS:" -ForegroundColor Yellow
    Write-Host "   ssh root@89.110.111.184" -ForegroundColor Cyan
    Write-Host "   mkdir -p ~/.ssh" -ForegroundColor Cyan
    Write-Host "   chmod 700 ~/.ssh" -ForegroundColor Cyan
    Write-Host "   echo 'PASTE_PUBLIC_KEY_HERE' >> ~/.ssh/authorized_keys" -ForegroundColor Cyan
    Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "[INFO] After setup, you can connect without password:" -ForegroundColor Green
Write-Host "   ssh ${VPS_USER}@${VPS_IP}" -ForegroundColor Cyan
