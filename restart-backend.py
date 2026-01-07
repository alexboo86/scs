#!/usr/bin/env python3
"""
Перезапуск backend контейнера
Использование: python restart-backend.py
"""

import paramiko
import sys
import time

VPS_IP = "89.110.111.184"
VPS_USER = "root"
PROJECT_DIR = "secure-content-service"
VPS_PROJECT_PATH = f"/root/projects/{PROJECT_DIR}"


def get_ssh_client(hostname: str, username: str, timeout: int = 10):
    """Создание SSH клиента"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=hostname,
            username=username,
            timeout=timeout,
            look_for_keys=True,
            allow_agent=True
        )
        return client
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return None


def execute_command(ssh_client, command, description):
    """Выполнение команды"""
    print(f"\n[INFO] {description}...")
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=60)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if output:
            print(output)
        if error and error.strip():
            print(f"[STDERR] {error}")
        
        return exit_status == 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    print("="*60)
    print("  Restart Backend Container")
    print("="*60)
    
    ssh_client = get_ssh_client(VPS_IP, VPS_USER)
    if not ssh_client:
        sys.exit(1)
    
    # Останавливаем контейнер
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose stop backend",
        "Stopping backend"
    )
    
    # Ждем немного
    print("\n[INFO] Waiting 3 seconds...")
    time.sleep(3)
    
    # Запускаем контейнер
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose up -d backend",
        "Starting backend"
    )
    
    # Ждем запуска
    print("\n[INFO] Waiting 5 seconds for container to start...")
    time.sleep(5)
    
    # Проверяем статус
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose ps backend",
        "Container status"
    )
    
    # Проверяем логи (последние 20 строк)
    print("\n[INFO] Recent logs:")
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose logs --tail=20 backend",
        "Recent logs"
    )
    
    ssh_client.close()
    
    print("\n" + "="*60)
    print("  Restart Complete")
    print("="*60)


if __name__ == "__main__":
    main()
