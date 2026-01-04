# Инструкция по интеграции с Tilda

## Шаг 1: Настройка сервера

### 1.1. Порт 8000

Порт настроен в `docker-compose.yml` на **8000**. Перезапустите контейнер:

```bash
docker-compose down
docker-compose up -d
```

### 1.2. Настройка переменных окружения

Создайте файл `.env` в корне проекта (или отредактируйте существующий):

```bash
# Secret key для безопасности (обязательно измените!)
SECRET_KEY=your-very-secret-key-change-this-in-production

# URL базы данных
DATABASE_URL=sqlite:///./data/database.db

# Разрешенные домены для CORS
# Разрешенные домены для CORS
ALLOWED_ORIGINS=http://185.88.159.33:8000,https://incrypto.tilda.ws

# Разрешенные домены для встраивания viewer (проверка Referer)
# Укажите домены вашего сайта Tilda через запятую
# Примеры:
# - Для Tilda: your-site.tilda.ws, your-site.tilda.cc
# - Для кастомного домена: yourdomain.com, www.yourdomain.com
ALLOWED_EMBED_DOMAINS=incrypto.tilda.ws

# ВАЖНО: Включите проверку Referer для защиты от прямого доступа
REQUIRE_REFERER_CHECK=true

# Максимальный размер файла (50MB)
MAX_FILE_SIZE=52428800

# Время жизни токена доступа (24 часа)
TOKEN_EXPIRY_HOURS=24
```

**ВАЖНО:** Замените `YOUR_EXTERNAL_IP` на ваш реальный внешний IP адрес (например, `185.123.45.67`).

### 1.3. Настройка файрвола

Убедитесь, что порт **8000** открыт в файрволе:

```bash
# Для Ubuntu/Debian (ufw)
sudo ufw allow 8000/tcp

# Для CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 1.4. Перезапуск сервиса

После изменения `.env` файла:

```bash
docker-compose down
docker-compose up -d
```

Проверьте, что сервис работает:

```bash
   curl http://localhost:8000/health
# Должен вернуть: {"status":"ok"}
```

---

## Шаг 2: Получение токена документа

### 2.1. Загрузите документ через админ-панель

1. Откройте админ-панель: `http://185.88.159.33:8000/admin`
2. Загрузите PDF или PPT/PPTX документ
3. После загрузки вы получите **Document Token** (access_token)

### 2.2. Сохраните токен документа

Сохраните `access_token` документа - он понадобится для встраивания на Tilda.

---

## Шаг 3: Встраивание на Tilda

### 3.1. Получение HTML кода для вставки

Используйте один из двух способов:

#### Способ 1: Прямое встраивание через iframe (рекомендуется)

Замените в коде ниже:
- `YOUR_EXTERNAL_IP` - на ваш внешний IP адрес
- `DOCUMENT_TOKEN` - на токен документа из админ-панели
- `USER_EMAIL` - на email пользователя (опционально, для водяных знаков)

```html
<iframe 
    src="http://185.88.159.33:8000/api/viewer/embed?document_token=DOCUMENT_TOKEN&user_email=USER_EMAIL"
    width="100%"
    height="800px"
    frameborder="0"
    allowfullscreen
    style="border: none; min-height: 600px;"
></iframe>
```

**Пример:**
```html
<iframe 
    src="http://185.123.45.67:8080/api/viewer/embed?document_token=doc_abc123xyz&user_email=student@example.com"
    width="100%"
    height="800px"
    frameborder="0"
    allowfullscreen
    style="border: none; min-height: 600px;"
></iframe>
```

#### Способ 2: Через JavaScript (рекомендуется для Tilda)

**Простой вариант (скопируйте и вставьте в HTML блок Tilda):**

```html
<div id="secure-content-viewer-container" style="width: 100%; height: 800px; min-height: 600px; position: relative;">
    <div id="viewer-loading" style="display: flex; justify-content: center; align-items: center; height: 100%; font-size: 18px; color: #666;">
        Загрузка документа...
    </div>
</div>

<script>
(function() {
    // ========== НАСТРОЙКИ ==========
    const SERVER_URL = 'http://185.88.159.33:8000';
    const DOCUMENT_TOKEN = 'DOCUMENT_TOKEN';  // Замените на токен документа
    
    // Получаем email из URL (если Tilda передает через ?email=user@example.com)
    const urlParams = new URLSearchParams(window.location.search);
    const userEmail = urlParams.get('email') || null;
    
    // Формируем URL
    let embedUrl = SERVER_URL + '/api/viewer/embed?document_token=' + encodeURIComponent(DOCUMENT_TOKEN);
    if (userEmail) {
        embedUrl += '&user_email=' + encodeURIComponent(userEmail);
    }
    
    // Создаем iframe
    const container = document.getElementById('secure-content-viewer-container');
    const loading = document.getElementById('viewer-loading');
    
    const iframe = document.createElement('iframe');
    iframe.src = embedUrl;
    iframe.width = '100%';
    iframe.height = '800px';
    iframe.frameBorder = '0';
    iframe.allowFullscreen = true;
    iframe.style.cssText = 'border: none; min-height: 600px; display: none;';
    iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-popups allow-forms');
    
    // Когда iframe загрузится
    iframe.onload = function() {
        loading.style.display = 'none';
        iframe.style.display = 'block';
    };
    
    // При ошибке загрузки
    iframe.onerror = function() {
        loading.textContent = 'Ошибка загрузки документа';
        loading.style.color = '#d32f2f';
    };
    
    container.appendChild(iframe);
})();
</script>
```

**Расширенный вариант (с дополнительными возможностями):**

См. файл `tilda-embed.js` в корне проекта - там полная версия с обработкой ошибок и дополнительными настройками.

### 3.2. Вставка кода в Tilda

1. **Откройте редактор страницы в Tilda**
2. **Добавьте блок "HTML"** (в разделе "Дополнительно")
3. **Вставьте HTML код** из способа 1 или 2 выше
4. **Сохраните страницу**

### 3.3. Настройка размера блока

В Tilda вы можете настроить размер блока с HTML кодом:
- **Ширина:** 100% (или фиксированная, например 1200px)
- **Высота:** 800px или больше (рекомендуется минимум 600px)

---

## Шаг 4: Настройка защиты (ВАЖНО!)

### 4.1. Включение проверки Referer

В файле `.env` установите:

```bash
REQUIRE_REFERER_CHECK=true
```

### 4.2. Указание доменов Tilda

В файле `.env` укажите домены вашего сайта Tilda:

```bash
ALLOWED_EMBED_DOMAINS=incrypto.tilda.ws
```

**Как узнать домен Tilda:**
- Откройте ваш сайт в браузере
- Посмотрите в адресной строке - домен будет вида `your-site.tilda.ws` или `your-site.tilda.cc`
- Если используете кастомный домен, добавьте его тоже: `yourdomain.com,www.yourdomain.com`

### 4.3. Перезапуск после изменений

```bash
docker-compose restart backend
```

---

## Шаг 5: Тестирование

### 5.1. Локальное тестирование

1. Откройте админ-панель: `http://185.88.159.33:8000/admin`
2. Загрузите тестовый документ
3. Скопируйте токен документа
4. Откройте в браузере: `http://185.88.159.33:8000/api/viewer/embed?document_token=YOUR_TOKEN`

### 5.2. Тестирование на Tilda

1. Вставьте код на страницу Tilda
2. Опубликуйте страницу
3. Откройте опубликованную страницу
4. Проверьте, что документ загружается и отображается корректно

---

## Шаг 6: Передача email пользователя из Tilda

Если у вас есть доступ к email пользователя в личном кабинете Tilda, вы можете передать его для водяных знаков:

### 6.1. Через JavaScript (если есть доступ к данным пользователя)

```html
<script>
// Получаем email пользователя из Tilda (пример)
// Замените на реальный способ получения email из вашего личного кабинета
const userEmail = window.tildaUserEmail || 'user@example.com';

const iframe = document.createElement('iframe');
iframe.src = `http://YOUR_EXTERNAL_IP:8080/api/viewer/embed?document_token=DOCUMENT_TOKEN&user_email=${encodeURIComponent(userEmail)}`;
// ... остальной код
</script>
```

### 6.2. Через параметры URL (если Tilda передает email в URL)

Если Tilda передает email в URL страницы (например, через параметр `?email=user@example.com`):

```html
<script>
// Получаем email из URL
const urlParams = new URLSearchParams(window.location.search);
const userEmail = urlParams.get('email') || 'guest@example.com';

const iframe = document.createElement('iframe');
iframe.src = `http://YOUR_EXTERNAL_IP:8080/api/viewer/embed?document_token=DOCUMENT_TOKEN&user_email=${encodeURIComponent(userEmail)}`;
// ... остальной код
</script>
```

---

## Часто задаваемые вопросы

### Q: Документ не загружается на Tilda

**A:** Проверьте:
1. Правильно ли указан внешний IP в коде
2. Открыт ли порт 8080 в файрволе
3. Включена ли проверка Referer и правильно ли указаны домены Tilda
4. Проверьте логи: `docker-compose logs backend`

### Q: Ошибка "Доступ разрешен только с разрешенных доменов"

**A:** 
1. Убедитесь, что `ALLOWED_EMBED_DOMAINS` содержит домен вашего сайта Tilda
2. Проверьте, что `REQUIRE_REFERER_CHECK=true`
3. Перезапустите backend: `docker-compose restart backend`

### Q: Как использовать HTTPS вместо HTTP?

**A:** 
1. Настройте reverse proxy (nginx/apache) с SSL сертификатом
2. Направьте трафик с порта 443 на порт 8080 контейнера
3. Обновите `ALLOWED_ORIGINS` и `ALLOWED_EMBED_DOMAINS` на HTTPS версии доменов

### Q: Можно ли использовать кастомный домен?

**A:** Да, просто добавьте ваш домен в `ALLOWED_EMBED_DOMAINS`:
```bash
ALLOWED_EMBED_DOMAINS=yourdomain.com,www.yourdomain.com,your-site.tilda.ws
```

---

## Примеры готовых кодов для Tilda

### Минимальный вариант (без email)

```html
<iframe 
    src="http://YOUR_EXTERNAL_IP:8080/api/viewer/embed?document_token=DOCUMENT_TOKEN"
    width="100%"
    height="800px"
    frameborder="0"
    allowfullscreen
    style="border: none; min-height: 600px;"
></iframe>
```

### С адаптивной высотой

```html
<div style="position: relative; padding-bottom: 75%; height: 0; overflow: hidden;">
    <iframe 
        src="http://YOUR_EXTERNAL_IP:8080/api/viewer/embed?document_token=DOCUMENT_TOKEN"
        style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
        frameborder="0"
        allowfullscreen
    ></iframe>
</div>
```

---

## Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker-compose logs backend --tail 100`
2. Проверьте доступность сервиса: `curl http://YOUR_EXTERNAL_IP:8080/health`
3. Убедитесь, что порт 8080 открыт и доступен извне
