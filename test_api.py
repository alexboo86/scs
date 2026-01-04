"""
Скрипт для тестирования API локально
"""
import requests
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8001"  # Изменен порт на 8001

def test_health():
    """Тест health check"""
    print("=" * 60)
    print("1. Тест Health Check")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def test_root():
    """Тест корневого endpoint"""
    print("\n" + "=" * 60)
    print("2. Тест Root Endpoint")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def test_create_user():
    """Тест создания пользователя"""
    print("\n" + "=" * 60)
    print("3. Тест создания пользователя")
    print("=" * 60)
    try:
        data = {
            "email": "test@example.com",
            "name": "Test User"
        }
        response = requests.post(f"{BASE_URL}/api/users/", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code in [200, 400]  # 400 если уже существует
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def test_list_users():
    """Тест списка пользователей"""
    print("\n" + "=" * 60)
    print("4. Тест списка пользователей")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/api/users/")
        print(f"Status: {response.status_code}")
        users = response.json()
        print(f"Найдено пользователей: {len(users)}")
        if users:
            print(f"Первый пользователь: {users[0]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def test_upload_document():
    """Тест загрузки документа (требует PDF файл)"""
    print("\n" + "=" * 60)
    print("5. Тест загрузки документа")
    print("=" * 60)
    
    # Ищем тестовый PDF в текущей директории или родительской
    test_pdf = None
    for path in [Path("."), Path(".."), Path("../..")]:
        for pdf_file in path.glob("*.pdf"):
            test_pdf = pdf_file
            break
        if test_pdf:
            break
    
    if not test_pdf or not test_pdf.exists():
        print("⚠️  PDF файл не найден для тестирования")
        print("   Пропускаем тест загрузки")
        return None
    
    try:
        print(f"Используем файл: {test_pdf}")
        with open(test_pdf, 'rb') as f:
            files = {'file': (test_pdf.name, f, 'application/pdf')}
            data = {
                'name': 'Test Document'
            }
            response = requests.post(
                f"{BASE_URL}/api/documents/upload",
                files=files,
                data=data
            )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Document ID: {result.get('id')}")
            print(f"Access Token: {result.get('access_token')}")
            print(f"Total Pages: {result.get('total_pages')}")
            return result
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def test_viewer_embed(document_token, user_email):
    """Тест embed endpoint"""
    print("\n" + "=" * 60)
    print("6. Тест Viewer Embed Endpoint")
    print("=" * 60)
    try:
        url = f"{BASE_URL}/api/viewer/embed"
        params = {
            "document_token": document_token,
            "user_email": user_email
        }
        response = requests.get(url, params=params)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Embed HTML получен успешно")
            print(f"Длина HTML: {len(response.text)} символов")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ SECURE CONTENT SERVICE API")
    print("=" * 60)
    
    results = []
    
    # Базовые тесты
    results.append(("Health Check", test_health()))
    results.append(("Root Endpoint", test_root()))
    results.append(("Create User", test_create_user()))
    results.append(("List Users", test_list_users()))
    
    # Тест загрузки документа
    doc_result = test_upload_document()
    if doc_result:
        document_token = doc_result.get('access_token')
        user_email = "test@example.com"
        
        # Предоставляем доступ
        print("\n" + "=" * 60)
        print("7. Предоставление доступа пользователю")
        print("=" * 60)
        try:
            doc_id = doc_result.get('id')
            response = requests.post(
                f"{BASE_URL}/api/admin/documents/{doc_id}/access",
                data={"user_emails": user_email}
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Ошибка: {e}")
        
        # Тест embed
        results.append(("Viewer Embed", test_viewer_embed(document_token, user_email)))
    
    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nПройдено: {passed}/{total}")

if __name__ == "__main__":
    main()
