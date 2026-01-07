#!/usr/bin/env python3
"""
Диагностика и исправление ошибки 502
Использование: python fix-502.py
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
    import os
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Пробуем с явным ключом
        ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")
        if os.path.exists(ssh_key_path):
            try:
                client.connect(
                    hostname=hostname,
                    username=username,
                    key_filename=ssh_key_path,
                    timeout=timeout,
                    look_for_keys=False
                )
                return client
            except:
                pass
        
        # Пробуем с автоматическим поиском
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
        print(f"[ERROR] Error type: {type(e).__name__}")
        return None


def execute_command(ssh_client, command, description, show_output=True):
    """Выполнение команды"""
    if show_output:
        print(f"\n[INFO] {description}...")
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=60)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if show_output:
            if output:
                print(output)
            if error and error.strip():
                print(f"[STDERR] {error}")
        
        return exit_status == 0, output, error
    except Exception as e:
        if show_output:
            print(f"[ERROR] {e}")
        return False, "", str(e)


def main():
    print("="*60)
    print("  502 Error Diagnostic & Fix")
    print("="*60)
    
    ssh_client = get_ssh_client(VPS_IP, VPS_USER)
    if not ssh_client:
        sys.exit(1)
    
    # 1. Проверка статуса контейнера
    print("\n" + "="*60)
    print("  Step 1: Checking container status")
    print("="*60)
    success, output, error = execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose ps",
        "Container status"
    )
    
    # 2. Проверка логов на ошибки
    print("\n" + "="*60)
    print("  Step 2: Checking backend logs for errors")
    print("="*60)
    success, logs, _ = execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose logs --tail=100 backend 2>&1 | grep -i 'error\\|exception\\|traceback\\|failed' || echo 'No obvious errors found'",
        "Error logs"
    )
    
    # 3. Проверка синтаксиса Python файлов
    print("\n" + "="*60)
    print("  Step 3: Checking Python syntax")
    print("="*60)
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose exec -T backend python -m py_compile /app/app/main.py 2>&1 || echo 'Syntax check failed'",
        "Main.py syntax"
    )
    
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose exec -T backend python -m py_compile /app/app/api/auth.py 2>&1 || echo 'Auth.py syntax check failed'",
        "Auth.py syntax"
    )
    
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose exec -T backend python -m py_compile /app/app/api/admin.py 2>&1 || echo 'Admin.py syntax check failed'",
        "Admin.py syntax"
    )
    
    # 4. Перезапуск контейнера
    print("\n" + "="*60)
    print("  Step 4: Restarting backend container")
    print("="*60)
    
    execute_command(ssh_client, f"cd {VPS_PROJECT_PATH} && docker-compose stop backend", "Stopping backend")
    time.sleep(2)
    execute_command(ssh_client, f"cd {VPS_PROJECT_PATH} && docker-compose up -d backend", "Starting backend")
    
    print("\n[INFO] Waiting 10 seconds for container to start...")
    time.sleep(10)
    
    # 5. Проверка после перезапуска
    print("\n" + "="*60)
    print("  Step 5: Checking status after restart")
    print("="*60)
    
    execute_command(ssh_client, f"cd {VPS_PROJECT_PATH} && docker-compose ps backend", "Container status")
    
    print("\n[INFO] Recent logs (last 30 lines):")
    execute_command(ssh_client, f"cd {VPS_PROJECT_PATH} && docker-compose logs --tail=30 backend", "Recent logs")
    
    # 6. Проверка health endpoint
    print("\n" + "="*60)
    print("  Step 6: Testing health endpoint")
    print("="*60)
    execute_command(
        ssh_client,
        f"cd {VPS_PROJECT_PATH} && docker-compose exec -T backend curl -f http://localhost:8000/health 2>&1 || echo 'Health check failed'",
        "Health check"
    )
    
    ssh_client.close()
    
    print("\n" + "="*60)
    print("  Diagnostic Complete")
    print("="*60)
    print("\nIf 502 persists, check:")
    print("  1. Nginx configuration (if used)")
    print("  2. Port 8000 is accessible")
    print("  3. Backend logs for Python errors")
    print("  4. Database connection issues")


if __name__ == "__main__":
    main()
