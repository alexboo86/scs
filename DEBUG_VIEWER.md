# Отладка Viewer

## Проблема: Viewer возвращает 404 или 403

### Статус исправлений

✅ **Endpoint `/viewer/` работает** - возвращает 403 вместо 404 (значит найден)

### Причины ошибок

1. **403 Forbidden** - Endpoint найден, но:
   - Проверка Referer блокирует доступ (если `REQUIRE_REFERER_CHECK=true`)
   - Токен невалидный или истек
   - Нет доступа у пользователя

2. **404 Not Found** - Endpoint не найден:
   - Неправильный URL (должен быть `/viewer/` с слешем или `/viewer` без слеша)
   - Роутер не подключен

## Решение проблем

### Проблема: 403 из-за проверки Referer

**Для локального тестирования:**

В файле `.env` установите:
```env
REQUIRE_REFERER_CHECK=false
```

Или в docker-compose.yml:
```yaml
environment:
  - REQUIRE_REFERER_CHECK=false
```

**Для продакшена:**

Укажите разрешенные домены:
```env
ALLOWED_EMBED_DOMAINS=your-site.tilda.ws,your-site.tilda.cc
REQUIRE_REFERER_CHECK=true
```

### Проблема: 403 из-за невалидного токена

1. Убедитесь что токен создан через `/api/viewer/token`
2. Проверьте что токен не истек (по умолчанию 24 часа)
3. Проверьте что пользователь имеет доступ к документу

### Проверка работоспособности

1. **Проверьте что endpoint доступен:**
   ```bash
   curl http://localhost:8001/viewer/?token=test
   ```
   Должен вернуть 403 (не 404) - значит endpoint найден

2. **Создайте валидный токен:**
   ```bash
   curl -X POST http://localhost:8001/api/viewer/token \
     -H "Content-Type: application/json" \
     -d '{"document_token": "YOUR_DOCUMENT_TOKEN", "user_email": "user@example.com"}'
   ```

3. **Откройте viewer с валидным токеном:**
   ```
   http://localhost:8001/viewer/?token=VIEWER_TOKEN
   ```

## Текущий статус

- ✅ Endpoint `/viewer/` зарегистрирован
- ✅ Endpoint `/api/viewer/` работает
- ✅ Проверка Referer отключена для локального тестирования (если `REQUIRE_REFERER_CHECK=false`)
- ⚠️  Для работы нужен валидный viewer token

## Следующие шаги для тестирования

1. Откройте админ-панель: http://localhost:8001/api/admin/
2. Создайте пользователя
3. Загрузите документ
4. Предоставьте доступ пользователю
5. Используйте Access Token для создания viewer token через API
6. Откройте viewer с полученным токеном
