#!/usr/bin/env python3
"""
Автоматический деплой на VPS через SSH/SFTP
Использование: python deploy.py
"""

import os
import sys
import paramiko
from pathlib import Path
from typing import Optional, Tuple
import time
import stat

# Настройки по умолчанию
VPS_IP = "89.110.111.184"
VPS_USER = "root"
PROJECT_DIR = "secure-content-service"
VPS_PROJECT_PATH = f"/root/projects/{PROJECT_DIR}"

# Исключаемые файлы и директории
EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyw',
    '.git',
    '.vscode',
    '*.log',
    '.env',
    'data',
    '*.db'
]


def should_exclude_file(file_path: Path) -> bool:
    """Проверка, нужно ли исключить файл"""
    file_str = str(file_path)
    
    # Проверяем паттерны исключения
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith('*'):
            # Расширение файла
            if file_path.suffix == pattern[1:]:
                return True
        elif pattern in file_str:
            return True
    
    return False


def get_ssh_client(hostname: str, username: str, timeout: int = 10) -> Optional[paramiko.SSHClient]:
    """Создание SSH клиента с автоматическим использованием SSH ключей"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Путь к SSH ключам
        ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")
        
        # Пробуем подключиться с ключом если он есть
        if os.path.exists(ssh_key_path):
            try:
                client.connect(
                    hostname=hostname,
                    username=username,
                    key_filename=ssh_key_path,
                    timeout=timeout,
                    look_for_keys=False,
                    allow_agent=False
                )
                return client
            except Exception as e1:
                print(f"[WARN] Failed to connect with key file: {e1}")
        
        # Пробуем подключиться с автоматическим поиском ключей
        try:
            client.connect(
                hostname=hostname,
                username=username,
                timeout=timeout,
                look_for_keys=True,
                allow_agent=True
            )
            return client
        except Exception as e2:
            print(f"[WARN] Failed to connect with auto keys: {e2}")
            raise
        
    except paramiko.AuthenticationException as e:
        print(f"[ERROR] Authentication failed: {e}")
        print("[INFO] Make sure SSH keys are configured. Run: setup-ssh-keys.ps1")
        return None
    except paramiko.SSHException as e:
        print(f"[ERROR] SSH error: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to connect to {hostname}: {e}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        print("[INFO] Check:")
        print("  1. Server is accessible")
        print("  2. SSH keys are configured")
        print("  3. Firewall allows SSH connection")
        return None


def create_remote_directory(sftp, remote_path: str):
    """Создание директории на удаленном сервере"""
    try:
        # Проверяем существование директории
        sftp.stat(remote_path)
    except IOError:
        # Директория не существует, создаем рекурсивно
        parts = remote_path.strip('/').split('/')
        current_path = ''
        for part in parts:
            if not part:
                continue
            current_path = f"{current_path}/{part}" if current_path else f"/{part}"
            try:
                sftp.stat(current_path)
            except IOError:
                try:
                    sftp.mkdir(current_path)
                except Exception:
                    pass  # Может уже существовать


def should_update_file(sftp, local_path: Path, remote_path: str) -> bool:
    """Проверка, нужно ли обновлять файл (сравнение размера и хеша)"""
    try:
        # Получаем информацию о локальном файле
        local_stat = local_path.stat()
        local_size = local_stat.st_size
        
        # Пробуем получить информацию о удаленном файле
        try:
            remote_stat = sftp.stat(remote_path)
            remote_size = remote_stat.st_size
            
            # Если размеры не совпадают, файл точно изменился
            if local_size != remote_size:
                return True
            
            # Если размеры совпадают, сравниваем хеши для надежности
            # Читаем первые 1KB файлов для быстрого сравнения
            # (полное чтение больших файлов может быть медленным)
            try:
                with open(local_path, 'rb') as f:
                    local_sample = f.read(1024)
                
                # Читаем удаленный файл через SFTP
                with sftp.open(remote_path, 'rb') as rf:
                    remote_sample = rf.read(1024)
                
                # Если первые байты не совпадают, файл изменился
                if local_sample != remote_sample:
                    return True
                
                # Если размеры и первые байты совпадают, файл не изменился
                return False
            except Exception:
                # Если не удалось сравнить содержимое, обновляем файл для безопасности
                return True
                
        except IOError:
            # Файл не существует на сервере, нужно загрузить
            return True
        
        return True
    except Exception as e:
        # В случае ошибки лучше обновить файл
        return True


def copy_file_sftp(sftp, local_path: Path, remote_path: str, check_changes: bool = True):
    """Копирование файла через SFTP"""
    try:
        # Проверяем, нужно ли обновлять файл
        if check_changes and not should_update_file(sftp, local_path, remote_path):
            return "skipped"
        
        # Создаем директорию если нужно
        remote_dir = os.path.dirname(remote_path)
        if remote_dir:
            create_remote_directory(sftp, remote_dir)
        
        # Копируем файл с проверкой размера
        local_size = local_path.stat().st_size
        sftp.put(str(local_path), remote_path)
        
        # Проверяем размер после передачи (с повторной попыткой при несовпадении)
        max_retries = 3
        for retry in range(max_retries):
            try:
                remote_stat = sftp.stat(remote_path)
                remote_size = remote_stat.st_size
                if remote_size == local_size:
                    break
                elif retry < max_retries - 1:
                    print(f"    [WARN] Size mismatch ({remote_size} != {local_size}), retrying ({retry + 1}/{max_retries})...")
                    sftp.put(str(local_path), remote_path)
                else:
                    raise Exception(f"Size mismatch after {max_retries} retries: {remote_size} != {local_size}")
            except Exception as e:
                if retry == max_retries - 1:
                    raise
                print(f"    [WARN] Error verifying file size: {e}, retrying...")
        
        return True
    except Exception as e:
        print(f"    [ERROR] Failed to copy {local_path.name}: {e}")
        return False


def sync_directory(ssh_client: paramiko.SSHClient, local_dir: Path, remote_base: str):
    """Синхронизация директории (только измененные файлы)"""
    print(f"[INFO] Syncing directory: {local_dir.name}")
    
    files_copied = 0
    files_skipped = 0
    files_failed = 0
    
    # Открываем SFTP сессию
    sftp = ssh_client.open_sftp()
    
    try:
        # Рекурсивно обходим все файлы
        for root, dirs, files in os.walk(local_dir):
            # Исключаем директории из списка для обхода
            dirs[:] = [d for d in dirs if not should_exclude_file(Path(root) / d)]
            
            for file in files:
                local_file = Path(root) / file
                
                # Проверяем, нужно ли исключить файл
                if should_exclude_file(local_file):
                    continue
                
                # Вычисляем относительный путь от local_dir
                try:
                    relative_path = local_file.relative_to(local_dir)
                except ValueError:
                    # Если не получается, используем имя файла
                    relative_path = Path(local_file.name)
                
                # Нормализуем путь для удаленного сервера
                remote_path = f"{remote_base}/{str(relative_path).replace(os.sep, '/')}"
                
                # Копируем файл (с проверкой изменений)
                result = copy_file_sftp(sftp, local_file, remote_path, check_changes=True)
                
                if result == True:
                    files_copied += 1
                    print(f"  -> {local_file.name} [UPDATED]")
                elif result == "skipped":
                    files_skipped += 1
                    # Не выводим пропущенные файлы, чтобы не засорять вывод
                else:
                    files_failed += 1
                    print(f"  -> {local_file.name} [FAILED]")
    finally:
        sftp.close()
    
    print(f"    Updated: {files_copied}, Skipped: {files_skipped}, Failed: {files_failed}")
    return files_copied, files_failed


def execute_ssh_command(ssh_client: paramiko.SSHClient, command: str, timeout: int = 30):
    """Выполнение команды через SSH"""
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        return exit_status == 0, output, error
    except Exception as e:
        print(f"[ERROR] Command failed: {e}")
        return False, "", str(e)


def main():
    """Основная функция"""
    print("=" * 50)
    print("  Auto Deploy to VPS (Python)")
    print("=" * 50)
    print()
    
    # Определяем путь к проекту
    script_dir = Path(__file__).parent.absolute()
    project_path = script_dir
    
    print(f"[INFO] Project path: {project_path}")
    print()
    
    # Подключаемся к серверу
    print("[INFO] Connecting to VPS...")
    ssh_client = get_ssh_client(VPS_IP, VPS_USER)
    
    if not ssh_client:
        print("[ERROR] Failed to establish SSH connection")
        print("[INFO] Make sure SSH keys are configured or run setup-ssh-keys.ps1")
        sys.exit(1)
    
    print("[INFO] Connection established")
    print()
    
    # Список директорий и файлов для синхронизации
    items_to_sync = [
        "backend/app",
        "frontend/templates",
        "docker-compose.yml",
        "nginx.conf"
    ]
    
    print("[INFO] Syncing files...")
    print()
    
    total_copied = 0
    total_failed = 0
    
    for item in items_to_sync:
        local_item = project_path / item
        
        if not local_item.exists():
            print(f"[WARN] Path not found: {item}")
            continue
        
        if local_item.is_dir():
            # Синхронизируем директорию
            remote_base = f"{VPS_PROJECT_PATH}/{item}"
            copied, failed = sync_directory(ssh_client, local_item, remote_base)
            total_copied += copied
            total_failed += failed
        else:
            # Копируем файл
            print(f"[INFO] Copying file: {item}")
            remote_path = f"{VPS_PROJECT_PATH}/{item}"
            
            sftp = ssh_client.open_sftp()
            try:
                result = copy_file_sftp(sftp, local_item, remote_path, check_changes=True)
                if result == True:
                    print(f"  -> {local_item.name} [UPDATED]")
                    total_copied += 1
                elif result == "skipped":
                    print(f"  -> {local_item.name} [SKIPPED - no changes]")
                else:
                    print(f"  -> {local_item.name} [FAILED]")
                    total_failed += 1
            finally:
                sftp.close()
        
        print()
    
    print(f"[INFO] Files updated: {total_copied}, Failed: {total_failed}")
    print()
    
    # Перезапускаем backend контейнер только если были изменения
    if total_copied == 0:
        print("[INFO] No files changed, skipping container restart")
    else:
        print("[INFO] Restarting backend container...")
        
        # Останавливаем
        execute_ssh_command(ssh_client, f"cd {VPS_PROJECT_PATH} && docker-compose stop backend", timeout=30)
        time.sleep(2)
        
        # Запускаем
        execute_ssh_command(ssh_client, f"cd {VPS_PROJECT_PATH} && docker-compose up -d backend", timeout=60)
        
        print("[INFO] Waiting 5 seconds for container to start...")
        time.sleep(5)
        
        # Проверяем статус
        success, output, error = execute_ssh_command(ssh_client, f"cd {VPS_PROJECT_PATH} && docker-compose ps backend", timeout=30)
        
        if success:
            print(output)
        else:
            print(f"[ERROR] Failed to check status: {error}")
        
        # Показываем последние логи
        print("\n[INFO] Recent logs (last 20 lines):")
        execute_ssh_command(ssh_client, f"cd {VPS_PROJECT_PATH} && docker-compose logs --tail=20 backend", timeout=30)
    
    # Проверяем, был ли обновлен nginx.conf
    nginx_updated = False
    for item in items_to_sync:
        if item == "nginx.conf":
            nginx_updated = True
            break
    
    # Если nginx.conf был обновлен, перезагружаем nginx
    if nginx_updated:
        print("\n[INFO] nginx.conf was updated, reloading nginx...")
        success, output, error = execute_ssh_command(
            ssh_client, 
            "sudo nginx -t && sudo systemctl reload nginx",
            timeout=30
        )
        if success:
            print("[INFO] Nginx reloaded successfully")
        else:
            print(f"[WARN] Failed to reload nginx: {error}")
            print("[INFO] You may need to reload nginx manually: sudo systemctl reload nginx")
    
    # Закрываем соединение
    ssh_client.close()
    
    print()
    print("=" * 50)
    print("  Deployment complete!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
