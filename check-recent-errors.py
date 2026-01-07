#!/usr/bin/env python3
"""
Проверка последних ошибок с большим количеством строк
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
    print("\n[INFO] Checking backend logs (last 200 lines, including stderr)...")
    
    # Проверяем и stdout и stderr
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker logs secure-content-backend --tail 200 2>&1 | grep -E '(ERROR|Exception|Traceback|500|upload)' -A 10 -B 5"
    )
    logs = stdout.read().decode()
    
    if logs.strip():
        print("\n" + "=" * 80)
        print("FOUND ERRORS/UPLOAD RELATED LOGS:")
        print("=" * 80)
        print(logs)
    else:
        print("\n[INFO] No errors found with grep. Showing last 100 lines:")
        stdin, stdout, stderr = ssh_client.exec_command(
            "docker logs secure-content-backend --tail 100 2>&1"
        )
        all_logs = stdout.read().decode()
        print(all_logs[-3000:])  # Последние ~100 строк

def main():
    print("=" * 80)
    print("  Check Recent Errors")
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
