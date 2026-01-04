# Инструкция по тестированию

## Статус сервиса

✅ **Сервис запущен и работает на порту 8001**

## Быстрые тесты

### 1. Health Check
```powershell
Invoke-WebRequest -Uri "http://localhost:8001/health"
```

### 2. API Документация
Откройте в браузере: http://localhost:8001/docs

### 3. Создание пользователя
```powershell
$body = @{
    email = "student@school.com"
    name = "Студент"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8001/api/users/" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

### 4. Список пользователей
```powershell
Invoke-WebRequest -Uri "http://localhost:8001/api/users/"
```

### 5. Загрузка документа
```powershell
$filePath = "путь\к\вашему\файлу.pdf"
$form = @{
    file = Get-Item $filePath
    name = "Тестовая презентация"
}

Invoke-WebRequest -Uri "http://localhost:8001/api/documents/upload" `
    -Method POST `
    -Form $form
```

### 6. Тестирование через Python скрипт
```powershell
python test_api.py
```

## Проверка логов

```powershell
docker-compose logs -f backend
```

## Остановка/Запуск

```powershell
# Остановка
docker-compose down

# Запуск
docker-compose up -d

# Перезапуск
docker-compose restart backend
```

## Известные проблемы и решения

### Порт 8000 занят
- Решение: Изменен порт на 8001 в docker-compose.yml
- Сервис доступен на http://localhost:8001

### Ошибка загрузки документа
- Проверьте логи: `docker-compose logs backend`
- Убедитесь что файл существует и доступен
- Проверьте формат файла (поддерживаются PDF, PPT, PPTX)

## Следующие шаги

1. Загрузите тестовый PDF документ
2. Создайте пользователя
3. Предоставьте доступ пользователю к документу
4. Протестируйте embed endpoint для Tilda
