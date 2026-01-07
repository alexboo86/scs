#!/usr/bin/env python3
"""
Проверка статуса сервера и логов
Использование: python check-status.py
"""

import paramiko
import sys

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
    """Выполнение команды и вывод результата"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print('='*60)
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=30)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if output:
            print(output)
        if error:
            print(f"[STDERR]\n{error}")
        
        return exit_status == 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    print("="*60)
    print("  Server Status Check")
    print("="*60)
    
    ssh_client = get_ssh_client(VPS_IP, VPS_USER)
    if not ssh_client:
        sys.exit(1)
    
    # Проверка статуса контейнеров
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose ps",
        "Container Status"
    )
    
    # Проверка логов backend (последние 50 строк)
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose logs --tail=50 backend",
        "Backend Logs (last 50 lines)"
    )
    
    # Проверка здоровья контейнера
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose exec -T backend curl -f http://localhost:8000/health || echo 'Health check failed'",
        "Health Check"
    )
    
    # Проверка портов
    execute_command(
        ssh_client,
        "netstat -tlnp | grep 8000 || ss -tlnp | grep 8000",
        "Port 8000 Status"
    )
    
    ssh_client.close()
    
    print("\n" + "="*60)
    print("  Check Complete")
    print("="*60)


if __name__ == "__main__":
    main()
