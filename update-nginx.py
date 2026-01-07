#!/usr/bin/env python3
"""
Обновление конфигурации nginx на сервере
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

def update_nginx_config(ssh_client):
    """Обновление конфигурации nginx"""
    # Читаем локальный nginx.conf
    local_nginx = Path(__file__).parent / "nginx.conf"
    if not local_nginx.exists():
        print(f"[ERROR] nginx.conf not found at {local_nginx}")
        return False
    
    with open(local_nginx, 'r', encoding='utf-8') as f:
        nginx_content = f.read()
    
    # Определяем путь к конфигурации на сервере
    # Проверяем, какой домен используется
    stdin, stdout, stderr = ssh_client.exec_command("ls /etc/nginx/sites-available/ | grep -E '(lessons|incrypto|secure)' | head -1")
    site_name = stdout.read().decode().strip()
    
    if not site_name:
        # Пробуем найти конфигурацию по server_name
        stdin, stdout, stderr = ssh_client.exec_command("grep -r 'lessons.incrypto.ru' /etc/nginx/sites-available/ 2>/dev/null | head -1 | cut -d: -f1")
        site_path = stdout.read().decode().strip()
        if site_path:
            site_name = Path(site_path).name
        else:
            print("[INFO] Using default site configuration")
            site_name = "default"
    
    remote_path = f"/etc/nginx/sites-available/{site_name}"
    print(f"[INFO] Updating nginx config at {remote_path}")
    
    # Копируем конфигурацию через SFTP
    sftp = ssh_client.open_sftp()
    try:
        # Создаем временный файл
        temp_path = f"/tmp/nginx_{site_name}.conf"
        with sftp.file(temp_path, 'w') as f:
            f.write(nginx_content)
        
        # Проверяем синтаксис
        stdin, stdout, stderr = ssh_client.exec_command(f"nginx -t -c /etc/nginx/nginx.conf")
        test_output = stdout.read().decode()
        test_error = stderr.read().decode()
        
        if "syntax is ok" in test_output or "syntax is ok" in test_error:
            # Копируем в финальное место
            stdin, stdout, stderr = ssh_client.exec_command(f"sudo cp {temp_path} {remote_path}")
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                # Перезагружаем nginx
                stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl reload nginx")
                reload_output = stdout.read().decode()
                reload_error = stderr.read().decode()
                
                if "reloaded" in reload_output.lower() or exit_status == 0:
                    print("[INFO] Nginx configuration updated and reloaded successfully")
                    # Удаляем временный файл
                    ssh_client.exec_command(f"rm -f {temp_path}")
                    return True
                else:
                    print(f"[ERROR] Failed to reload nginx: {reload_error}")
            else:
                print(f"[ERROR] Failed to copy config file")
        else:
            print(f"[ERROR] Nginx syntax check failed:")
            print(test_error)
            print("[INFO] Configuration NOT applied due to syntax errors")
    finally:
        sftp.close()
    
    return False

def main():
    print("=" * 50)
    print("  Update Nginx Configuration")
    print("=" * 50)
    
    ssh_client = get_ssh_client()
    if not ssh_client:
        return
    
    try:
        if update_nginx_config(ssh_client):
            print("\n" + "=" * 50)
            print("  Nginx update complete!")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("  Nginx update failed!")
            print("=" * 50)
    finally:
        ssh_client.close()

if __name__ == "__main__":
    main()
