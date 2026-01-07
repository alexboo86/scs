#!/usr/bin/env python3
"""
Скрипт для проверки размера базы данных и диска на сервере
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
    print("  Database Space Check")
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
        # Проверка свободного места на диске
        print("[INFO] Checking disk space...")
        success, output, error = execute_ssh_command(ssh_client, "df -h /")
        if success:
            print(output)
        else:
            print(f"[ERROR] Failed to check disk space: {error}")
        
        # Проверка размера базы данных
        db_path = f"{VPS_PROJECT_PATH}/backend/data/database.db"
        print(f"\n[INFO] Checking database size at {db_path}...")
        success, output, error = execute_ssh_command(ssh_client, f"ls -lh {db_path}")
        if success:
            print(output)
        else:
            print(f"[WARN] Database file not found or error: {error}")
        
        # Проверка размера директории data
        print(f"\n[INFO] Checking data directory size...")
        success, output, error = execute_ssh_command(ssh_client, f"du -sh {VPS_PROJECT_PATH}/backend/data")
        if success:
            print(output)
        
        # Проверка размера директории cache
        print(f"\n[INFO] Checking cache directory size...")
        success, output, error = execute_ssh_command(ssh_client, f"du -sh {VPS_PROJECT_PATH}/backend/cache")
        if success:
            print(output)
        
        # Проверка размера директории uploads
        print(f"\n[INFO] Checking uploads directory size...")
        success, output, error = execute_ssh_command(ssh_client, f"du -sh {VPS_PROJECT_PATH}/backend/uploads")
        if success:
            print(output)
        
        # Подсчет количества записей в viewing_sessions
        print(f"\n[INFO] Checking viewing_sessions table...")
        success, output, error = execute_ssh_command(
            ssh_client,
            f"cd {VPS_PROJECT_PATH}/backend && docker exec secure-content-backend python -c \"from app.models.database import SessionLocal, ViewingSession; db = SessionLocal(); count = db.query(ViewingSession).count(); print(f'Total sessions: {{count}}'); db.close()\""
        )
        if success:
            print(output)
        else:
            print(f"[WARN] Could not check sessions count: {error}")
        
        # Проверка старых сессий (старше 7 дней)
        print(f"\n[INFO] Checking old sessions (older than 7 days)...")
        success, output, error = execute_ssh_command(
            ssh_client,
            f"cd {VPS_PROJECT_PATH}/backend && docker exec secure-content-backend python -c \"from app.models.database import SessionLocal, ViewingSession; from datetime import datetime, timedelta; db = SessionLocal(); old_date = datetime.utcnow() - timedelta(days=7); count = db.query(ViewingSession).filter(ViewingSession.created_at < old_date).count(); print(f'Old sessions (>7 days): {{count}}'); db.close()\""
        )
        if success:
            print(output)
        else:
            print(f"[WARN] Could not check old sessions: {error}")
        
    finally:
        ssh_client.close()
    
    print("\n" + "=" * 60)
    print("  Check complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
