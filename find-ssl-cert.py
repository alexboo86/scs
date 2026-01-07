#!/usr/bin/env python3
"""
Поиск SSL сертификатов на сервере
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

def find_ssl_certs(ssh_client):
    """Поиск SSL сертификатов"""
    print("\n[INFO] Searching for SSL certificates...")
    
    # Проверяем letsencrypt
    stdin, stdout, stderr = ssh_client.exec_command(
        "ls -la /etc/letsencrypt/live/ 2>&1"
    )
    letsencrypt_dirs = stdout.read().decode()
    print("\nLetsencrypt directories:")
    print(letsencrypt_dirs)
    
    # Проверяем текущую конфигурацию nginx
    stdin, stdout, stderr = ssh_client.exec_command(
        "grep -r 'ssl_certificate' /etc/nginx/sites-enabled/ 2>&1 | head -5"
    )
    nginx_ssl = stdout.read().decode()
    print("\nCurrent nginx SSL configuration:")
    print(nginx_ssl)
    
    # Проверяем домен lessons.incrypto.ru
    stdin, stdout, stderr = ssh_client.exec_command(
        "ls -la /etc/letsencrypt/live/lessons.incrypto.ru/ 2>&1"
    )
    lessons_cert = stdout.read().decode()
    print("\nLessons.incrypto.ru certificate:")
    print(lessons_cert)

def main():
    print("=" * 80)
    print("  Find SSL Certificates")
    print("=" * 80)
    
    ssh_client = get_ssh_client()
    if not ssh_client:
        return
    
    try:
        find_ssl_certs(ssh_client)
    finally:
        ssh_client.close()

if __name__ == "__main__":
    main()
