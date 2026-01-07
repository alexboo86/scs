#!/usr/bin/env python3
"""
Автоматическая очистка кеша изображений на сервере
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

def clear_cache(ssh_client):
    """Очистка кеша изображений"""
    print("[INFO] Clearing image cache...")
    
    # Подсчитываем файлы до удаления
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker exec secure-content-backend find /app/data/cache -name 'watermarked_*.png' -type f 2>/dev/null | wc -l"
    )
    before_count = stdout.read().decode().strip()
    print(f"[INFO] Files before cleanup: {before_count}")
    
    # Удаляем файлы
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker exec secure-content-backend find /app/data/cache -name 'watermarked_*.png' -type f -delete 2>&1"
    )
    result = stdout.read().decode()
    error = stderr.read().decode()
    
    if error and "No such file" not in error:
        print(f"[WARN] {error}")
    
    # Подсчитываем файлы после удаления
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker exec secure-content-backend find /app/data/cache -name 'watermarked_*.png' -type f 2>/dev/null | wc -l"
    )
    after_count = stdout.read().decode().strip()
    print(f"[INFO] Files after cleanup: {after_count}")
    print("[INFO] Cache cleared successfully")

def main():
    print("=" * 50)
    print("  Clear Image Cache")
    print("=" * 50)
    
    ssh_client = get_ssh_client()
    if not ssh_client:
        return
    
    try:
        clear_cache(ssh_client)
        print("\n" + "=" * 50)
        print("  Cache cleanup complete!")
        print("=" * 50)
    finally:
        ssh_client.close()

if __name__ == "__main__":
    main()
