#!/usr/bin/env python3
"""
Скрипт для очистки всех логов на сервере
"""
import paramiko
import os
from pathlib import Path

# Конфигурация подключения
VPS_HOST = "185.88.159.33"
VPS_USER = "root"
SSH_KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")
VPS_PROJECT_PATH = "/root/projects/secure-content-service"

def execute_ssh_command(ssh_client: paramiko.SSHClient, command: str):
    """Выполнение команды через SSH"""
    stdin, stdout, stderr = ssh_client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    return exit_status == 0, output, error

def main():
    print("=" * 60)
    print("  Server Logs Cleanup")
    print("=" * 60)
    
    # Подключение к серверу
    print(f"\n[INFO] Connecting to {VPS_HOST}...")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
        ssh_client.connect(VPS_HOST, username=VPS_USER, pkey=ssh_key)
        print("[INFO] Connection established\n")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return
    
    try:
        # Проверка свободного места ДО очистки
        print("[INFO] Checking disk space BEFORE cleanup...")
        success, output, error = execute_ssh_command(ssh_client, "df -h /")
        if success:
            print(output)
        
        # 1. Очистка логов Docker контейнеров
        print("\n[INFO] Cleaning Docker container logs...")
        success, output, error = execute_ssh_command(
            ssh_client,
            "docker ps -a --format '{{.Names}}' | xargs -I {} sh -c 'echo > /var/lib/docker/containers/$(docker inspect --format={{.Id}} {})/*-json.log 2>/dev/null || true'"
        )
        if success:
            print("[INFO] Docker container logs cleared")
        else:
            # Альтернативный способ - через truncate
            print("[INFO] Trying alternative method...")
            success, output, error = execute_ssh_command(
                ssh_client,
                "find /var/lib/docker/containers/ -name '*-json.log' -exec truncate -s 0 {} \;"
            )
            if success:
                print("[INFO] Docker container logs cleared (alternative method)")
            else:
                print(f"[WARN] Could not clear Docker logs: {error}")
        
        # 2. Очистка логов приложения (если есть)
        print("\n[INFO] Cleaning application logs...")
        app_logs_path = f"{VPS_PROJECT_PATH}/backend/logs"
        success, output, error = execute_ssh_command(
            ssh_client,
            f"find {app_logs_path} -name '*.log' -type f -exec truncate -s 0 {{}} \; 2>/dev/null || true"
        )
        if success:
            print("[INFO] Application logs cleared")
        
        # 3. Очистка системных логов
        print("\n[INFO] Cleaning system logs...")
        log_commands = [
            "journalctl --vacuum-time=1d",  # Удалить логи старше 1 дня
            "journalctl --vacuum-size=100M",  # Оставить только 100MB логов
            "truncate -s 0 /var/log/syslog 2>/dev/null || true",
            "truncate -s 0 /var/log/messages 2>/dev/null || true",
            "truncate -s 0 /var/log/kern.log 2>/dev/null || true",
            "truncate -s 0 /var/log/auth.log 2>/dev/null || true",
            "truncate -s 0 /var/log/daemon.log 2>/dev/null || true",
        ]
        
        for cmd in log_commands:
            success, output, error = execute_ssh_command(ssh_client, cmd)
            if success:
                print(f"[INFO] Executed: {cmd.split()[0]}")
        
        # 4. Очистка логов Nginx
        print("\n[INFO] Cleaning Nginx logs...")
        nginx_logs = [
            "/var/log/nginx/access.log",
            "/var/log/nginx/error.log",
            "/var/log/nginx/access.log.1",
            "/var/log/nginx/error.log.1",
        ]
        
        for log_file in nginx_logs:
            success, output, error = execute_ssh_command(
                ssh_client,
                f"truncate -s 0 {log_file} 2>/dev/null || true"
            )
            if success:
                print(f"[INFO] Cleared: {log_file}")
        
        # 5. Очистка старых логов (ротация)
        print("\n[INFO] Cleaning old rotated logs...")
        success, output, error = execute_ssh_command(
            ssh_client,
            "find /var/log -name '*.log.*' -type f -mtime +7 -delete 2>/dev/null || true"
        )
        if success:
            print("[INFO] Old rotated logs cleaned")
        
        success, output, error = execute_ssh_command(
            ssh_client,
            "find /var/log -name '*.gz' -type f -mtime +7 -delete 2>/dev/null || true"
        )
        if success:
            print("[INFO] Old compressed logs cleaned")
        
        # 6. Очистка временных файлов
        print("\n[INFO] Cleaning temporary files...")
        temp_commands = [
            "rm -rf /tmp/* 2>/dev/null || true",
            "rm -rf /var/tmp/* 2>/dev/null || true",
        ]
        
        for cmd in temp_commands:
            success, output, error = execute_ssh_command(ssh_client, cmd)
            if success:
                print(f"[INFO] Temporary files cleaned")
        
        # 7. Очистка кеша пакетов (опционально)
        print("\n[INFO] Cleaning package cache...")
        success, output, error = execute_ssh_command(
            ssh_client,
            "apt-get clean 2>/dev/null || yum clean all 2>/dev/null || true"
        )
        if success:
            print("[INFO] Package cache cleaned")
        
        # Проверка свободного места ПОСЛЕ очистки
        print("\n[INFO] Checking disk space AFTER cleanup...")
        success, output, error = execute_ssh_command(ssh_client, "df -h /")
        if success:
            print(output)
        
        # Показываем размер самых больших директорий
        print("\n[INFO] Top 10 largest directories:")
        success, output, error = execute_ssh_command(
            ssh_client,
            "du -h / 2>/dev/null | sort -rh | head -10"
        )
        if success:
            print(output)
        
    except Exception as e:
        print(f"[ERROR] Error during cleanup: {e}")
    finally:
        ssh_client.close()
    
    print("\n" + "=" * 60)
    print("  Cleanup complete!")
    print("=" * 60)
    print("\n[INFO] If disk is still full, check:")
    print("  1. Database size: docker exec secure-content-backend ls -lh /app/data/database.db")
    print("  2. Cache directory: docker exec secure-content-backend du -sh /app/cache")
    print("  3. Uploads directory: docker exec secure-content-backend du -sh /app/uploads")
    print("  4. Run database cleanup: docker exec secure-content-backend python cleanup_old_sessions.py")

if __name__ == "__main__":
    main()
