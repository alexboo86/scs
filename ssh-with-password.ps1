# Функция для выполнения SSH команд с паролем
function Invoke-SSHWithPassword {
    param(
        [string]$Host,
        [string]$User,
        [string]$Password,
        [string]$Command
    )
    
    # Используем plink (PuTTY) если доступен, иначе обычный ssh
    if (Get-Command plink -ErrorAction SilentlyContinue) {
        $plinkCmd = "echo y | plink -ssh -pw `"$Password`" ${User}@${Host} `"$Command`""
        Invoke-Expression $plinkCmd
    } else {
        # Для обычного ssh нужен expect или sshpass
        # В Windows лучше использовать SSH ключи
        Write-Host "[WARN] Password authentication requires plink or SSH keys" -ForegroundColor Yellow
        Write-Host "[INFO] Please setup SSH keys using: .\setup-ssh-keys.ps1" -ForegroundColor Cyan
        ssh "${User}@${Host}" $Command
    }
}
