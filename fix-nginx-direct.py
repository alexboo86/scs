#!/usr/bin/env python3
"""
Прямое исправление конфигурации nginx на сервере
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

def fix_nginx_config(ssh_client):
    """Исправление конфигурации nginx"""
    print("[INFO] Reading current nginx config...")
    
    # Читаем текущую конфигурацию
    stdin, stdout, stderr = ssh_client.exec_command(
        "cat /etc/nginx/sites-available/lessons.incrypto.ru"
    )
    current_config = stdout.read().decode()
    
    print("\n[INFO] Current config (first 50 lines):")
    print(current_config[:2000])
    
    # Заменяем пути к сертификатам и добавляем client_max_body_size
    fixed_config = current_config.replace(
        "/etc/letsencrypt/live/185.88.159.33/fullchain.pem",
        "/etc/letsencrypt/live/lessons.incrypto.ru/fullchain.pem"
    ).replace(
        "/etc/letsencrypt/live/185.88.159.33/privkey.pem",
        "/etc/letsencrypt/live/lessons.incrypto.ru/privkey.pem"
    )
    
    # Добавляем client_max_body_size если его нет
    if "client_max_body_size" not in fixed_config:
        # Ищем место после server_name для добавления
        if "server_name" in fixed_config and "client_max_body_size" not in fixed_config:
            # Добавляем после ssl_prefer_server_ciphers on;
            if "ssl_prefer_server_ciphers on;" in fixed_config:
                fixed_config = fixed_config.replace(
                    "ssl_prefer_server_ciphers on;",
                    "ssl_prefer_server_ciphers on;\n    \n    # Увеличиваем лимит размера загружаемых файлов\n    client_max_body_size 100M;\n    client_body_buffer_size 128k;"
                )
            else:
                # Добавляем после ssl_ciphers
                fixed_config = fixed_config.replace(
                    "ssl_ciphers HIGH:!aNULL:!MD5;",
                    "ssl_ciphers HIGH:!aNULL:!MD5;\n    ssl_prefer_server_ciphers on;\n    \n    # Увеличиваем лимит размера загружаемых файлов\n    client_max_body_size 100M;\n    client_body_buffer_size 128k;"
                )
    
    # Добавляем таймауты если их нет
    if "proxy_connect_timeout" not in fixed_config:
        fixed_config = fixed_config.replace(
            "proxy_request_buffering off;",
            "proxy_request_buffering off;\n        \n        # Увеличиваем таймауты для больших файлов\n        proxy_connect_timeout 300s;\n        proxy_send_timeout 300s;\n        proxy_read_timeout 300s;"
        )
    
    # Сохраняем во временный файл
    sftp = ssh_client.open_sftp()
    try:
        temp_path = "/tmp/nginx_lessons.conf"
        with sftp.file(temp_path, 'w') as f:
            f.write(fixed_config)
        
        # Проверяем синтаксис
        stdin, stdout, stderr = ssh_client.exec_command(f"nginx -t -c /etc/nginx/nginx.conf 2>&1")
        test_output = stdout.read().decode()
        test_error = stderr.read().decode()
        
        # Проверяем синтаксис новой конфигурации
        stdin, stdout, stderr = ssh_client.exec_command(
            f"cat {temp_path} | nginx -t -c /dev/stdin 2>&1 || echo 'TEST_FAILED'"
        )
        syntax_test = stdout.read().decode() + stderr.read().decode()
        
        if "syntax is ok" in syntax_test or "TEST_FAILED" not in syntax_test:
            # Копируем в финальное место
            stdin, stdout, stderr = ssh_client.exec_command(f"sudo cp {temp_path} /etc/nginx/sites-available/lessons.incrypto.ru")
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                # Перезагружаем nginx
                stdin, stdout, stderr = ssh_client.exec_command("sudo nginx -t && sudo systemctl reload nginx")
                reload_output = stdout.read().decode()
                reload_error = stderr.read().decode()
                
                if "syntax is ok" in reload_output or exit_status == 0:
                    print("\n[INFO] Nginx configuration updated and reloaded successfully")
                    return True
                else:
                    print(f"\n[ERROR] Failed to reload nginx: {reload_error}")
            else:
                print(f"\n[ERROR] Failed to copy config file")
        else:
            print(f"\n[ERROR] Nginx syntax check failed:")
            print(syntax_test)
    finally:
        sftp.close()
    
    return False

def main():
    print("=" * 80)
    print("  Fix Nginx Configuration Directly")
    print("=" * 80)
    
    ssh_client = get_ssh_client()
    if not ssh_client:
        return
    
    try:
        if fix_nginx_config(ssh_client):
            print("\n" + "=" * 80)
            print("  Nginx fix complete!")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("  Nginx fix failed!")
            print("=" * 80)
    finally:
        ssh_client.close()

if __name__ == "__main__":
    main()
