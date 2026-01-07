#!/usr/bin/env python3
"""
Проверка логов и очистка кеша изображений
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

def check_logs(ssh_client):
    """Проверка логов контейнера"""
    print("\n[INFO] Checking backend logs...")
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker logs secure-content-backend --tail 50 2>&1"
    )
    logs = stdout.read().decode()
    print(logs)
    
    # Проверяем ошибки
    if "ERROR" in logs or "error" in logs.lower():
        print("\n[WARN] Found errors in logs!")

def check_cache_files(ssh_client):
    """Проверка файлов в кеше"""
    print("\n[INFO] Checking cache directory...")
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker exec secure-content-backend find /app/data/cache -name '*.png' -type f | head -5"
    )
    cache_files = stdout.read().decode().strip()
    if cache_files:
        print("Sample cache files:")
        print(cache_files)
        
        # Проверяем размер одного файла
        if cache_files:
            first_file = cache_files.split('\n')[0]
            stdin, stdout, stderr = ssh_client.exec_command(
                f"docker exec secure-content-backend ls -lh '{first_file}'"
            )
            file_info = stdout.read().decode()
            print(f"\nFile info for {first_file}:")
            print(file_info)
    else:
        print("No cache files found")

def clear_cache(ssh_client):
    """Очистка кеша изображений"""
    print("\n[INFO] Clearing image cache...")
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker exec secure-content-backend find /app/data/cache -name 'watermarked_*.png' -type f -delete"
    )
    result = stdout.read().decode()
    error = stderr.read().decode()
    
    if error:
        print(f"[ERROR] {error}")
    else:
        print("[INFO] Cache cleared successfully")
        
        # Подсчитываем удаленные файлы
        stdin, stdout, stderr = ssh_client.exec_command(
            "docker exec secure-content-backend find /app/data/cache -name 'watermarked_*.png' -type f | wc -l"
        )
        remaining = stdout.read().decode().strip()
        print(f"[INFO] Remaining watermarked files: {remaining}")

def test_image_endpoint(ssh_client):
    """Тест эндпоинта изображения"""
    print("\n[INFO] Testing image endpoint...")
    # Получаем токен из последнего документа
    stdin, stdout, stderr = ssh_client.exec_command(
        "docker exec secure-content-backend python -c \"from app.models.database import Document, ViewingSession; from app.database import SessionLocal; db = SessionLocal(); doc = db.query(Document).first(); session = db.query(ViewingSession).filter(ViewingSession.document_id == doc.id).first() if doc else None; print(session.viewer_token if session else 'No session')\" 2>&1"
    )
    token = stdout.read().decode().strip()
    print(f"Viewer token: {token[:20]}..." if token else "No token found")
    
    if token:
        stdin, stdout, stderr = ssh_client.exec_command(
            f"curl -I http://localhost:8000/api/documents/1/page/1?viewer_token={token} 2>&1 | head -20"
        )
        headers = stdout.read().decode()
        print("\nResponse headers:")
        print(headers)

def main():
    print("=" * 50)
    print("  Check Logs and Cache")
    print("=" * 50)
    
    ssh_client = get_ssh_client()
    if not ssh_client:
        return
    
    try:
        check_logs(ssh_client)
        check_cache_files(ssh_client)
        
        response = input("\nClear cache? (y/n): ")
        if response.lower() == 'y':
            clear_cache(ssh_client)
        
        test_image_endpoint(ssh_client)
        
    finally:
        ssh_client.close()

if __name__ == "__main__":
    main()
