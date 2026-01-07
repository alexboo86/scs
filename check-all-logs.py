#!/usr/bin/env python3
"""
Проверка всех логов - nginx и backend
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

def check_all_logs(ssh_client):
    """Проверка всех логов"""
    print("\n" + "=" * 80)
    print("BACKEND LOGS (last 50 lines):")
    print("=" * 80)
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker logs secure-content-backend --tail 50 2>&1"
    )
    backend_logs = stdout.read().decode()
    print(backend_logs)
    
    print("\n" + "=" * 80)
    print("NGINX ERROR LOGS (last 30 lines):")
    print("=" * 80)
    stdin, stdout, stderr = ssh_client.exec_command(
        "tail -30 /var/log/nginx/error.log 2>&1"
    )
    nginx_error_logs = stdout.read().decode()
    print(nginx_error_logs)
    
    print("\n" + "=" * 80)
    print("NGINX ACCESS LOGS (last 20 lines, filtering upload):")
    print("=" * 80)
    stdin, stdout, stderr = ssh_client.exec_command(
        "tail -100 /var/log/nginx/access.log 2>&1 | grep -i upload | tail -20"
    )
    nginx_access_logs = stdout.read().decode()
    if nginx_access_logs.strip():
        print(nginx_access_logs)
    else:
        print("No upload requests found in nginx access log")
        
    # Проверяем последние запросы к /api/documents/upload
    print("\n" + "=" * 80)
    print("LAST REQUESTS TO /api/documents/upload:")
    print("=" * 80)
    stdin, stdout, stderr = ssh_client.exec_command(
        "tail -100 /var/log/nginx/access.log 2>&1 | grep '/api/documents/upload' | tail -10"
    )
    upload_logs = stdout.read().decode()
    if upload_logs.strip():
        print(upload_logs)
    else:
        print("No upload requests found")

def main():
    print("=" * 80)
    print("  Check All Logs")
    print("=" * 80)
    
    ssh_client = get_ssh_client()
    if not ssh_client:
        return
    
    try:
        check_all_logs(ssh_client)
    finally:
        ssh_client.close()

if __name__ == "__main__":
    main()
