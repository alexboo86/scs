# Setup SSH keys for passwordless access
# Usage: .\setup-ssh-keys.ps1

param(
    [string]$VPS_IP = "89.110.111.184",
    [string]$VPS_USER = "root"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SSH Keys Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if SSH key already exists
$sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa"
$sshPubKeyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"

if (-not (Test-Path $sshKeyPath)) {
    Write-Host "[INFO] Generating SSH key pair..." -ForegroundColor Green
    ssh-keygen -t rsa -b 4096 -f $sshKeyPath -N '""' -q
    Write-Host "[INFO] SSH key pair generated" -ForegroundColor Green
} else {
    Write-Host "[INFO] SSH key already exists" -ForegroundColor Yellow
}

# Read public key
$publicKey = Get-Content $sshPubKeyPath -ErrorAction SilentlyContinue

if (-not $publicKey) {
    Write-Host "[ERROR] Failed to read public key" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[INFO] Copying public key to VPS..." -ForegroundColor Green
Write-Host "[INFO] You will need to enter password ONCE" -ForegroundColor Yellow
Write-Host ""

# Copy public key to VPS
$tempFile = [System.IO.Path]::GetTempFileName()
$publicKey | Out-File -FilePath $tempFile -Encoding ASCII

try {
    # Try using ssh-copy-id if available
    if (Get-Command ssh-copy-id -ErrorAction SilentlyContinue) {
        ssh-copy-id -i $sshPubKeyPath "${VPS_USER}@${VPS_IP}"
    } else {
        # Manual method - use ssh-copy-id or manual copy
        Write-Host ""
        Write-Host "[INFO] Using manual method to copy SSH key..." -ForegroundColor Green
        Write-Host ""
        Write-Host "You can use one of these methods:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Method 1 (Recommended): Use ssh-copy-id manually" -ForegroundColor Cyan
        Write-Host "  ssh-copy-id -i $sshPubKeyPath ${VPS_USER}@${VPS_IP}" -ForegroundColor White
        Write-Host ""
        Write-Host "Method 2: Copy key manually" -ForegroundColor Cyan
        Write-Host "  Type this command and paste password when asked:" -ForegroundColor White
        $publicKeyContent = Get-Content $sshPubKeyPath -Raw
        $publicKeyContent = $publicKeyContent.Trim()
        $manualCommand = "type `"$sshPubKeyPath`" | ssh ${VPS_USER}@${VPS_IP} `"mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`""
        Write-Host "  $manualCommand" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Method 3: Copy public key below and add manually:" -ForegroundColor Cyan
        Write-Host $publicKeyContent -ForegroundColor White
        Write-Host ""
        Write-Host "Then SSH to server and run:" -ForegroundColor Yellow
        Write-Host "  mkdir -p ~/.ssh" -ForegroundColor White
        Write-Host "  chmod 700 ~/.ssh" -ForegroundColor White
        Write-Host "  echo 'PASTE_KEY_HERE' >> ~/.ssh/authorized_keys" -ForegroundColor White
        Write-Host "  chmod 600 ~/.ssh/authorized_keys" -ForegroundColor White
        Write-Host ""
        
        # Try Method 2 automatically
        Write-Host "[INFO] Trying Method 2 automatically..." -ForegroundColor Green
        Write-Host "[INFO] Enter password when prompted (you can paste with Ctrl+V):" -ForegroundColor Yellow
        Write-Host ""
        
        $publicKeyContent = Get-Content $sshPubKeyPath -Raw
        $publicKeyContent = $publicKeyContent.Trim()
        $remoteCommand = "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$publicKeyContent' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
        
        ssh "${VPS_USER}@${VPS_IP}" $remoteCommand
    }
    
    Write-Host ""
    Write-Host "[INFO] Testing passwordless connection..." -ForegroundColor Green
    
    # Test connection
    $testResult = ssh -o BatchMode=yes -o ConnectTimeout=5 "${VPS_USER}@${VPS_IP}" "echo 'SSH key works!'" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] SSH key setup complete! Passwordless access enabled." -ForegroundColor Green
        Write-Host ""
        Write-Host "You can now use deploy scripts without entering password." -ForegroundColor Cyan
    } else {
        Write-Host "[WARN] SSH key may not be working. Please check manually." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "[ERROR] Failed to copy SSH key: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual setup:" -ForegroundColor Yellow
    Write-Host "1. Copy this public key:" -ForegroundColor Yellow
    Write-Host $publicKey -ForegroundColor White
    Write-Host ""
    Write-Host "2. SSH to server and run:" -ForegroundColor Yellow
    Write-Host "   mkdir -p ~/.ssh" -ForegroundColor White
    Write-Host "   chmod 700 ~/.ssh" -ForegroundColor White
    Write-Host "   echo '$publicKey' >> ~/.ssh/authorized_keys" -ForegroundColor White
    Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor White
} finally {
    if (Test-Path $tempFile) {
        Remove-Item $tempFile -Force
    }
}
