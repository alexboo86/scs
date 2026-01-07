#!/usr/bin/env python3
"""
Скрипт для очистки старых записей из базы данных
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
    print("  Database Cleanup")
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
        # Сначала проверяем количество записей
        print("[INFO] Checking current session count...")
        success, output, error = execute_ssh_command(
            ssh_client,
            f"cd {VPS_PROJECT_PATH}/backend && docker exec secure-content-backend python -c \"from app.models.database import SessionLocal, ViewingSession; db = SessionLocal(); count = db.query(ViewingSession).count(); print(f'Total sessions: {{count}}'); db.close()\""
        )
        if success:
            print(output)
        
        # Удаляем старые сессии (старше 7 дней)
        print("\n[INFO] Deleting old sessions (older than 7 days)...")
        success, output, error = execute_ssh_command(
            ssh_client,
            f"cd {VPS_PROJECT_PATH}/backend && docker exec secure-content-backend python -c \"from app.models.database import SessionLocal, ViewingSession; from datetime import datetime, timedelta; db = SessionLocal(); old_date = datetime.utcnow() - timedelta(days=7); deleted = db.query(ViewingSession).filter(ViewingSession.created_at < old_date).delete(); db.commit(); print(f'Deleted {{deleted}} old sessions'); db.close()\""
        )
        if success:
            print(output)
        else:
            print(f"[ERROR] Failed to delete old sessions: {error}")
            return
        
        # Проверяем количество записей после очистки
        print("\n[INFO] Checking session count after cleanup...")
        success, output, error = execute_ssh_command(
            ssh_client,
            f"cd {VPS_PROJECT_PATH}/backend && docker exec secure-content-backend python -c \"from app.models.database import SessionLocal, ViewingSession; db = SessionLocal(); count = db.query(ViewingSession).count(); print(f'Remaining sessions: {{count}}'); db.close()\""
        )
        if success:
            print(output)
        
        # Оптимизируем базу данных (VACUUM)
        print("\n[INFO] Optimizing database (VACUUM)...")
        success, output, error = execute_ssh_command(
            ssh_client,
            f"cd {VPS_PROJECT_PATH}/backend && docker exec secure-content-backend python -c \"from app.models.database import engine; engine.execute('VACUUM'); print('Database optimized')\""
        )
        if success:
            print(output)
        else:
            # Попробуем через sqlite3 напрямую
            print("[INFO] Trying VACUUM via sqlite3...")
            db_path = f"{VPS_PROJECT_PATH}/backend/data/database.db"
            success, output, error = execute_ssh_command(
                ssh_client,
                f"docker exec secure-content-backend sqlite3 {db_path} 'VACUUM;'"
            )
            if success:
                print("[INFO] Database optimized")
            else:
                print(f"[WARN] Could not optimize database: {error}")
        
        # Проверяем размер базы данных после очистки
        print("\n[INFO] Checking database size after cleanup...")
        db_path = f"{VPS_PROJECT_PATH}/backend/data/database.db"
        success, output, error = execute_ssh_command(ssh_client, f"ls -lh {db_path}")
        if success:
            print(output)
        
    finally:
        ssh_client.close()
    
    print("\n" + "=" * 60)
    print("  Cleanup complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
