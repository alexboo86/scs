#!/usr/bin/env python3
"""
Проверка логов ошибок на сервере
"""

import paramiko
from pathlib import Path

VPS_IP = "89.110.111.184"
VPS_USER = "root"
SSH_KEY_PATH = Path.home() / ".ssh" / "id_rsa"

def get_ssh_client():
    """Подключение к серверу через SSH"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(
            hostname=VPS_IP,
            username=VPS_USER,
            key_filename=str(SSH_KEY_PATH),
            timeout=10
        )
        return ssh
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return None

def check_logs(ssh_client):
    """Проверка логов контейнера"""
    print("\n[INFO] Checking backend logs (last 100 lines)...")
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker logs secure-content-backend --tail 100 2>&1"
    )
    logs = stdout.read().decode()
    
    # Ищем ошибки
    if "ERROR" in logs or "Traceback" in logs or "Exception" in logs:
        print("\n" + "=" * 80)
        print("ERRORS FOUND:")
        print("=" * 80)
        lines = logs.split('\n')
        for i, line in enumerate(lines):
            if "ERROR" in line or "Traceback" in line or "Exception" in line:
                # Показываем контекст вокруг ошибки
                start = max(0, i - 5)
                end = min(len(lines), i + 20)
                print("\n".join(lines[start:end]))
                print("-" * 80)
    else:
        print("\n[INFO] No obvious errors found in logs")
        print("\nLast 50 lines:")
        print(logs[-2000:])  # Последние ~50 строк

def main():
    print("=" * 80)
    print("  Check Error Logs")
    print("=" * 80)
    
    ssh_client = get_ssh_client()
    if not ssh_client:
        return
    
    try:
        check_logs(ssh_client)
    finally:
        ssh_client.close()

if __name__ == "__main__":
    main()
