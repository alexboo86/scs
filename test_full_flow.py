"""
Полный тест рабочего процесса:
1. Создание пользователя
2. Загрузка документа
3. Предоставление доступа
4. Создание viewer token
5. Открытие viewer
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_full_flow():
    print("=" * 60)
    print("ПОЛНЫЙ ТЕСТ РАБОЧЕГО ПРОЦЕССА")
    print("=" * 60)
    
    # 1. Создание пользователя
    print("\n1. Создание пользователя...")
    user_data = {
        "email": "student@school.com",
        "name": "Тестовый студент"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/users/", json=user_data)
        if response.status_code in [200, 400]:  # 400 если уже существует
            print(f"   [OK] Пользователь создан или уже существует")
            user = response.json() if response.status_code == 200 else None
        else:
            print(f"   ❌ Ошибка: {response.status_code}")
            return
    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
        return
    
    # 2. Загрузка документа (требует PDF файл)
    print("\n2. Загрузка документа...")
    print("   [INFO] Требуется PDF файл для тестирования")
    print("   Пропускаем этот шаг для демонстрации")
    
    # Для теста используем существующий документ если есть
    try:
        docs_response = requests.get(f"{BASE_URL}/api/documents/")
        if docs_response.status_code == 200:
            documents = docs_response.json()
            if documents:
                doc = documents[0]
                document_token = doc['access_token']
                document_id = doc['id']
                print(f"   ✅ Найден документ: {doc['name']} (ID: {doc['id']})")
                print(f"   Access Token: {document_token}")
            else:
                print("   ⚠️  Документов нет. Загрузите документ через админ-панель")
                print(f"   Админ-панель: {BASE_URL}/api/admin/")
                return
        else:
            print(f"   ❌ Ошибка получения документов: {docs_response.status_code}")
            return
    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
        return
    
    # 3. Предоставление доступа
    print("\n3. Предоставление доступа пользователю...")
    try:
        access_data = {"user_emails": "student@school.com"}
        response = requests.post(
            f"{BASE_URL}/api/admin/documents/{document_id}/access",
            data=access_data
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Доступ предоставлен: {result.get('success', 0)} успешно")
        else:
            print(f"   ⚠️  Ошибка или доступ уже есть: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
    
    # 4. Создание viewer token
    print("\n4. Создание viewer token...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/viewer/token",
            json={
                "document_token": document_token,
                "user_email": "student@school.com"
            }
        )
        if response.status_code == 200:
            token_data = response.json()
            viewer_token = token_data['viewer_token']
            print(f"   [OK] Viewer token создан: {viewer_token[:20]}...")
            print(f"   Viewer URL: {token_data['viewer_url']}")
        else:
            print(f"   [ERROR] Ошибка создания token: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return
    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
        return
    
    # 5. Проверка viewer
    print("\n5. Проверка viewer endpoint...")
    try:
        viewer_url = f"{BASE_URL}/viewer/?token={viewer_token}"
        response = requests.get(viewer_url)
        if response.status_code == 200:
            print(f"   [OK] Viewer работает! Status: {response.status_code}")
            print(f"   URL: {viewer_url}")
        else:
            print(f"   [WARN] Status: {response.status_code}")
            print(f"   Ответ: {response.text[:200]}")
    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    print(f"\nАдмин-панель: {BASE_URL}/api/admin/")
    print(f"API документация: {BASE_URL}/docs")

if __name__ == "__main__":
    test_full_flow()
