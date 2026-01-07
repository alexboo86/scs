# Automatic deploy without password (uses SSH keys)
# Usage: .\deploy-auto.ps1

param(
    [string]$VPS_IP = "89.110.111.184",
    [string]$VPS_USER = "root",
    [string]$PROJECT_DIR = "secure-content-service"
)

$ErrorActionPreference = "Stop"

# Get project path automatically
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_PATH = $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Auto Deploy to VPS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to execute SSH commands (passwordless)
function Invoke-SSHCommand {
    param([string]$Command)
    
    ssh -o BatchMode=yes "${VPS_USER}@${VPS_IP}" $Command
}

# Function to copy file (passwordless) - using SFTP
function Copy-FileToVPS {
    param([string]$LocalPath, [string]$RemotePath)
    
    Write-Host "  -> $LocalPath" -ForegroundColor Yellow
    
    # Expand ~ to home directory and normalize path
    $RemotePathExpanded = $RemotePath -replace '^~/', '/root/'
    $RemoteDir = Split-Path $RemotePathExpanded -Parent
    $RemoteFileName = Split-Path $RemotePathExpanded -Leaf
    
    # Create directory on VPS if needed (using SSH, not SFTP - SFTP mkdir doesn't support -p)
    Invoke-SSHCommand "mkdir -p `"$RemoteDir`"" | Out-Null
    
    # Convert Windows path to forward slashes for SFTP
    $localPathFixed = $LocalPath -replace '\\', '/'
    
    # Create SFTP batch script
    $sftpScript = [System.IO.Path]::GetTempFileName()
    
    # SFTP commands - directories already created via SSH, just cd and put
    $sftpCommands = @"
cd `"$RemoteDir`"
put `"$localPathFixed`" `"$RemoteFileName`"
quit
"@
    
    $sftpCommands | Out-File -FilePath $sftpScript -Encoding ASCII -NoNewline
    
    try {
        # Use SFTP with batch mode (uses SSH keys automatically)
        # Use Job for timeout support
        $sftpJob = Start-Job -ScriptBlock {
            param($script, $user, $ip)
            & sftp -b $script "${user}@${ip}" 2>&1
        } -ArgumentList $sftpScript, $VPS_USER, $VPS_IP
        
        # Wait for job with timeout (30 seconds)
        $completedJob = $sftpJob | Wait-Job -Timeout 30
        
        # Check if job completed or timed out
        if ($completedJob) {
            # Job completed
            $result = Receive-Job $sftpJob
            Remove-Job $sftpJob -Force
            # Check for errors in output
            if ($result) {
                $errorMsg = $result -join "`n"
                if ($errorMsg -match "error|failed|denied" -and $errorMsg -notmatch "Changing to" -and $errorMsg -notmatch "Connected to" -and $errorMsg -notmatch "sftp>") {
                    Write-Host "    [WARN] SFTP may have failed" -ForegroundColor Yellow
                }
            }
        } else {
            # Timeout - job still running
            Stop-Job $sftpJob -ErrorAction SilentlyContinue
            Remove-Job $sftpJob -Force -ErrorAction SilentlyContinue
            Write-Host "    [WARN] SFTP timed out after 30 seconds" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    [ERROR] SFTP failed: $_" -ForegroundColor Red
    } finally {
        # Clean up temp script
        if (Test-Path $sftpScript) {
            Remove-Item $sftpScript -Force -ErrorAction SilentlyContinue
        }
    }
}

# Test connection
Write-Host "[INFO] Testing SSH connection..." -ForegroundColor Green
try {
    $testResult = Invoke-SSHCommand "echo 'Connected'"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[INFO] Connection established" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to connect to VPS" -ForegroundColor Red
        Write-Host "[INFO] Run .\setup-ssh-keys.ps1 first to setup SSH keys" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[ERROR] Failed to connect to VPS: $_" -ForegroundColor Red
    Write-Host "[INFO] Run .\setup-ssh-keys.ps1 first to setup SSH keys" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[INFO] Syncing files..." -ForegroundColor Green

# List of directories and files to update
$itemsToUpdate = @(
    "backend\app",
    "frontend\templates",
    "docker-compose.yml"
)

foreach ($item in $itemsToUpdate) {
    $LocalItem = Join-Path $PROJECT_PATH $item
    
    if (Test-Path $LocalItem) {
        if (Test-Path $LocalItem -PathType Container) {
            # This is a directory - copy all files
            Write-Host "[INFO] Syncing directory: $item" -ForegroundColor Cyan
            
            $VPSItem = "~/projects/${PROJECT_DIR}/${item}"
            
            # Copy files recursively (exclude __pycache__ and .pyc files)
            Get-ChildItem -Path $LocalItem -Recurse -File | Where-Object {
                $fullName = $_.FullName
                $fullName -notlike '*__pycache__*' -and
                $_.Extension -ne '.pyc' -and
                $_.Extension -ne '.pyo' -and
                $_.Extension -ne '.pyw'
            } | ForEach-Object {
                $relativePath = $_.FullName.Substring($PROJECT_PATH.Length + 1)
                # Convert Windows path separators to forward slashes
                $relativePathFixed = $relativePath -replace '\\', '/'
                $vpsFilePath = "~/projects/${PROJECT_DIR}/${relativePathFixed}"
                Copy-FileToVPS -LocalPath $_.FullName -RemotePath $vpsFilePath
            }
        } else {
            # This is a file
            Write-Host "[INFO] Copying file: $item" -ForegroundColor Cyan
            $VPSItem = "~/projects/${PROJECT_DIR}/${item}"
            Copy-FileToVPS -LocalPath $LocalItem -RemotePath $VPSItem
        }
    }
}

Write-Host ""
Write-Host "[INFO] Files copied!" -ForegroundColor Green

# Restart backend
Write-Host ""
Write-Host "[INFO] Restarting backend container..." -ForegroundColor Green

Invoke-SSHCommand "cd ~/projects/$PROJECT_DIR"
Invoke-SSHCommand "docker-compose restart backend"
Write-Host ""
Invoke-SSHCommand "docker-compose ps"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deployment complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
