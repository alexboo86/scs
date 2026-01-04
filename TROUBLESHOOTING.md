# Решение проблем с встраиванием на Tilda

## Проблема: "Загрузка документа..." но ничего не происходит

### Диагностика

1. **Откройте консоль браузера на странице Tilda:**
   - Нажмите F12
   - Перейдите на вкладку "Console"
   - Ищите ошибки с префиксом `[Secure Content Viewer]`

2. **Проверьте вкладку Network:**
   - F12 → Network
   - Обновите страницу
   - Ищите запросы к `185.88.159.33:8000`
   - Если запросов нет → браузер блокирует (Mixed Content)
   - Если запросы есть, но ошибка → проверьте логи сервера

3. **Проверьте логи сервера:**
   ```bash
   docker-compose logs backend --tail 50 --follow
   ```

### Возможные причины и решения

#### 1. Mixed Content (HTTPS → HTTP)

**Проблема:** Tilda использует HTTPS, а сервер HTTP. Браузеры блокируют загрузку HTTP контента с HTTPS страниц.

**Решение:**
- **Вариант А:** Настроить HTTPS на сервере (рекомендуется)
- **Вариант Б:** Использовать reverse proxy (nginx) с SSL сертификатом
- **Вариант В:** Временно разрешить Mixed Content в браузере (только для тестирования)

**Для тестирования (Chrome):**
1. Откройте Chrome
2. В адресной строке введите: `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
3. Добавьте: `https://incrypto.tilda.ws`
4. Перезапустите браузер

#### 2. CORS блокировка

**Проверка:** В консоли браузера должна быть ошибка типа:
```
Access to fetch at 'http://185.88.159.33:8000/...' from origin 'https://incrypto.tilda.ws' has been blocked by CORS policy
```

**Решение:** Убедитесь, что в `.env` файле:
```bash
ALLOWED_ORIGINS=http://185.88.159.33:8000,https://incrypto.tilda.ws
```

#### 3. Referer проверка блокирует

**Проверка:** В логах сервера должно быть:
```
[EMBED] Access denied - referer not allowed
```

**Решение:** Убедитесь, что:
```bash
ALLOWED_EMBED_DOMAINS=incrypto.tilda.ws
REQUIRE_REFERER_CHECK=true
```

#### 4. Файрвол блокирует порт 8000

**Проверка:** Попробуйте открыть напрямую в браузере:
```
http://185.88.159.33:8000/health
```

Должно вернуть: `{"status":"ok"}`

**Решение:** Откройте порт 8000 в файрволе:
```bash
sudo ufw allow 8000/tcp
```

### Быстрая проверка

Выполните в терминале на сервере:

```bash
# Проверка доступности сервера
curl http://185.88.159.33:8000/health

# Проверка настроек
docker-compose exec backend python -c "from app.core.config import settings; print('ALLOWED_ORIGINS:', settings.ALLOWED_ORIGINS); print('REQUIRE_REFERER_CHECK:', settings.REQUIRE_REFERER_CHECK)"

# Проверка логов в реальном времени
docker-compose logs backend --follow
```

### Тестовый запрос

Попробуйте открыть напрямую в браузере (замените TOKEN на реальный):
```
http://185.88.159.33:8000/api/viewer/embed?document_token=-lsSDMgIfCNYGA8PMvph91Wg2bcppe3oZVfLuQIRi-A
```

Если открывается напрямую, но не работает на Tilda → проблема в Mixed Content или CORS.

### Временное решение для тестирования

Если нужно быстро протестировать, можно временно использовать HTTP версию Tilda (если доступна):
- Откройте `http://incrypto.tilda.ws` вместо `https://incrypto.tilda.ws`
- Это обойдет проблему Mixed Content

**ВНИМАНИЕ:** Это только для тестирования! В продакшене нужен HTTPS на сервере.
