# Deploy with password input
# Usage: .\deploy-with-password.ps1

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
Write-Host "  Deploy to VPS (with password)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Request password from user (plain text for easy paste)
Write-Host "Enter VPS password (you can paste with Ctrl+V or right-click):" -ForegroundColor Yellow
$VPS_PASSWORD = Read-Host

Write-Host ""
Write-Host "[INFO] Connecting to VPS..." -ForegroundColor Green

# Function to execute SSH commands with password
function Invoke-SSHCommand {
    param([string]$Command)
    
    if (Get-Command plink -ErrorAction SilentlyContinue) {
        $plinkCmd = "echo y | plink -ssh -pw `"$VPS_PASSWORD`" ${VPS_USER}@${VPS_IP} `"$Command`""
        Invoke-Expression $plinkCmd 2>&1
    } else {
        if (Get-Command sshpass -ErrorAction SilentlyContinue) {
            $env:SSHPASS = $VPS_PASSWORD
            sshpass -e ssh "${VPS_USER}@${VPS_IP}" $Command
        } else {
            Write-Host "[WARN] plink and sshpass not found. Using regular ssh." -ForegroundColor Yellow
            Write-Host "[WARN] You may need to enter password manually." -ForegroundColor Yellow
            ssh "${VPS_USER}@${VPS_IP}" $Command
        }
    }
}

# Function to copy file
function Copy-FileToVPS {
    param([string]$LocalPath, [string]$RemotePath)
    
    Write-Host "  -> $LocalPath" -ForegroundColor Yellow
    
    # Create directory on VPS if needed
    $RemoteDir = Split-Path $RemotePath -Parent
    Invoke-SSHCommand "mkdir -p `"$RemoteDir`"" | Out-Null
    
    # Copy file
    if (Get-Command pscp -ErrorAction SilentlyContinue) {
        $pscpCmd = "echo y | pscp -pw `"$VPS_PASSWORD`" `"$LocalPath`" ${VPS_USER}@${VPS_IP}:`"$RemotePath`""
        Invoke-Expression $pscpCmd 2>&1 | Out-Null
    } elseif (Get-Command scp -ErrorAction SilentlyContinue) {
        if (Get-Command sshpass -ErrorAction SilentlyContinue) {
            $env:SSHPASS = $VPS_PASSWORD
            sshpass -e scp "`"$LocalPath`" ${VPS_USER}@${VPS_IP}:`"$RemotePath`"" 2>&1 | Out-Null
        } else {
            scp "`"$LocalPath`" ${VPS_USER}@${VPS_IP}:`"$RemotePath`"" 2>&1 | Out-Null
        }
    }
}

# Test connection
try {
    $testResult = Invoke-SSHCommand "echo 'Connected'"
    if ($LASTEXITCODE -eq 0 -or $testResult) {
        Write-Host "[INFO] Connection established" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to connect to VPS" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] Failed to connect to VPS: $_" -ForegroundColor Red
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
            
            # Copy files recursively
            Get-ChildItem -Path $LocalItem -Recurse -File | ForEach-Object {
                $relativePath = $_.FullName.Substring($PROJECT_PATH.Length + 1)
                $vpsFilePath = "~/projects/${PROJECT_DIR}/${relativePath}"
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

# Execute commands separately to avoid parsing issues
Invoke-SSHCommand "cd ~/projects/$PROJECT_DIR"
Invoke-SSHCommand "docker-compose restart backend"
Write-Host ""
Invoke-SSHCommand "docker-compose ps"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deployment complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# Clear password from memory
$VPS_PASSWORD = $null
