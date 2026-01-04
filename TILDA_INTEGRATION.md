# Интеграция с Tilda

## Быстрый старт

### 1. Настройка сервиса

В файле `.env` укажите ваш домен Tilda:

```env
# Разрешенные домены для встраивания (через запятую)
ALLOWED_EMBED_DOMAINS=your-site.tilda.ws,your-site.tilda.cc,your-custom-domain.com

# Включить проверку Referer (защита от прямого доступа)
REQUIRE_REFERER_CHECK=true
```

### 2. Получение токенов

Перед встраиванием вам нужно:

1. **Загрузить документ** через API и получить `access_token`
2. **Создать пользователя** или использовать существующего
3. **Предоставить доступ** пользователю к документу

### 3. HTML код для Tilda

Вставьте этот код в блок "HTML" на странице Tilda:

```html
<div id="secure-content-viewer"></div>

<script>
(function() {
    // Конфигурация
    const CONFIG = {
        // URL вашего сервиса (без слеша в конце)
        serviceUrl: 'https://your-content-service.com',
        
        // Токен документа (получен при загрузке)
        documentToken: 'YOUR_DOCUMENT_ACCESS_TOKEN',
        
        // Email пользователя (из личного кабинета Tilda)
        userEmail: 'user@example.com',
        
        // Высота viewer (можно настроить)
        height: '800px'
    };
    
    // Создаем iframe
    const container = document.getElementById('secure-content-viewer');
    const iframe = document.createElement('iframe');
    
    iframe.src = `${CONFIG.serviceUrl}/api/viewer/embed?document_token=${CONFIG.documentToken}&user_email=${encodeURIComponent(CONFIG.userEmail)}`;
    iframe.style.width = '100%';
    iframe.style.height = CONFIG.height;
    iframe.style.border = 'none';
    iframe.style.minHeight = '600px';
    iframe.setAttribute('allowfullscreen', '');
    iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-popups allow-forms');
    
    // Показываем загрузку
    container.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;">Загрузка документа...</div>';
    
    // Добавляем iframe после загрузки
    iframe.onload = function() {
        container.innerHTML = '';
        container.appendChild(iframe);
    };
    
    iframe.onerror = function() {
        container.innerHTML = '<div style="text-align: center; padding: 50px; color: #d32f2f;">Ошибка загрузки документа</div>';
    };
    
    // Предзагружаем iframe
    container.appendChild(iframe);
})();
</script>
```

## Динамическая интеграция с личным кабинетом

Если у вас есть личный кабинет пользователя на Tilda, можно динамически подставлять данные:

```html
<div id="secure-content-viewer"></div>

<script>
(function() {
    // Получаем данные из вашей системы (например, из localStorage или через API)
    function getUserData() {
        // Пример: получение из localStorage (вы должны сохранить туда при входе)
        const userData = JSON.parse(localStorage.getItem('userData') || '{}');
        return {
            email: userData.email || 'guest@example.com',
            documentToken: userData.documentToken || 'DEFAULT_TOKEN'
        };
    }
    
    // Конфигурация
    const CONFIG = {
        serviceUrl: 'https://your-content-service.com',
        height: '800px'
    };
    
    const userData = getUserData();
    
    if (!userData.email || !userData.documentToken) {
        document.getElementById('secure-content-viewer').innerHTML = 
            '<div style="text-align: center; padding: 50px; color: #d32f2f;">Необходима авторизация</div>';
        return;
    }
    
    // Создаем iframe
    const container = document.getElementById('secure-content-viewer');
    const iframe = document.createElement('iframe');
    
    iframe.src = `${CONFIG.serviceUrl}/api/viewer/embed?document_token=${userData.documentToken}&user_email=${encodeURIComponent(userData.email)}`;
    iframe.style.width = '100%';
    iframe.style.height = CONFIG.height;
    iframe.style.border = 'none';
    iframe.style.minHeight = '600px';
    iframe.setAttribute('allowfullscreen', '');
    
    container.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;">Загрузка документа...</div>';
    
    iframe.onload = function() {
        container.innerHTML = '';
        container.appendChild(iframe);
    };
    
    container.appendChild(iframe);
})();
</script>
```

## Интеграция через ваш backend

Если у вас есть свой backend, который управляет доступом:

```html
<div id="secure-content-viewer"></div>

<script>
(async function() {
    const CONFIG = {
        serviceUrl: 'https://your-content-service.com',
        yourApiUrl: 'https://your-backend.com/api',
        height: '800px'
    };
    
    try {
        // Получаем токен от вашего API
        const response = await fetch(`${CONFIG.yourApiUrl}/get-viewer-token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer YOUR_JWT_TOKEN' // Если используется
            },
            body: JSON.stringify({
                document_id: 123 // ID документа из вашей системы
            })
        });
        
        const data = await response.json();
        
        if (!data.viewer_url) {
            throw new Error('Не удалось получить токен');
        }
        
        // Создаем iframe
        const container = document.getElementById('secure-content-viewer');
        const iframe = document.createElement('iframe');
        
        iframe.src = data.viewer_url;
        iframe.style.width = '100%';
        iframe.style.height = CONFIG.height;
        iframe.style.border = 'none';
        iframe.style.minHeight = '600px';
        iframe.setAttribute('allowfullscreen', '');
        
        container.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;">Загрузка документа...</div>';
        
        iframe.onload = function() {
            container.innerHTML = '';
            container.appendChild(iframe);
        };
        
        container.appendChild(iframe);
        
    } catch (error) {
        document.getElementById('secure-content-viewer').innerHTML = 
            `<div style="text-align: center; padding: 50px; color: #d32f2f;">Ошибка: ${error.message}</div>`;
    }
})();
</script>
```

## Настройка для разных страниц

Если на разных страницах показываются разные документы:

```html
<div id="secure-content-viewer"></div>

<script>
(function() {
    // Получаем ID документа из URL или data-атрибута
    const urlParams = new URLSearchParams(window.location.search);
    const documentId = urlParams.get('doc') || document.getElementById('secure-content-viewer').dataset.documentId;
    
    // Маппинг ID документа на токены (можно хранить в вашем backend)
    const documentTokens = {
        '1': 'TOKEN_FOR_DOC_1',
        '2': 'TOKEN_FOR_DOC_2',
        // ...
    };
    
    const CONFIG = {
        serviceUrl: 'https://your-content-service.com',
        userEmail: 'user@example.com', // или из localStorage
        height: '800px'
    };
    
    const documentToken = documentTokens[documentId];
    
    if (!documentToken) {
        document.getElementById('secure-content-viewer').innerHTML = 
            '<div style="text-align: center; padding: 50px; color: #d32f2f;">Документ не найден</div>';
        return;
    }
    
    // ... остальной код как выше
})();
</script>
```

## Адаптивность для мобильных

Viewer автоматически адаптируется под мобильные устройства. Для лучшего опыта добавьте:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
```

И настройте высоту для мобильных:

```javascript
const height = window.innerWidth < 768 ? '100vh' : '800px';
iframe.style.height = height;
```

## Безопасность

✅ **Защита от прямого доступа**: Viewer открывается только с разрешенных доменов  
✅ **Проверка Referer**: Сервер проверяет источник запроса  
✅ **Токенизация**: Каждая сессия имеет уникальный токен  
✅ **Ограниченное время жизни**: Токены истекают через 24 часа  

## Troubleshooting

### Viewer не загружается

1. Проверьте, что домен Tilda добавлен в `ALLOWED_EMBED_DOMAINS`
2. Проверьте, что `REQUIRE_REFERER_CHECK=true` (если нужна защита)
3. Проверьте консоль браузера на ошибки
4. Убедитесь, что токен документа и email пользователя корректны

### Ошибка "Доступ запрещен"

1. Убедитесь, что пользователю предоставлен доступ к документу
2. Проверьте, что email пользователя совпадает с email в системе
3. Проверьте срок действия токена

### Viewer открывается напрямую

Если viewer открывается при прямом переходе по ссылке, убедитесь что:
- `REQUIRE_REFERER_CHECK=true` в `.env`
- Домен указан в `ALLOWED_EMBED_DOMAINS`

## Пример полной интеграции

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <h1>Мой курс</h1>
    
    <div id="secure-content-viewer"></div>
    
    <script>
    (function() {
        const CONFIG = {
            serviceUrl: 'https://your-content-service.com',
            documentToken: 'YOUR_DOCUMENT_TOKEN',
            userEmail: 'student@school.com',
            height: window.innerWidth < 768 ? '100vh' : '800px'
        };
        
        const container = document.getElementById('secure-content-viewer');
        
        // Проверка наличия данных
        if (!CONFIG.documentToken || !CONFIG.userEmail) {
            container.innerHTML = '<div style="padding: 50px; text-align: center; color: #d32f2f;">Необходима авторизация</div>';
            return;
        }
        
        const iframe = document.createElement('iframe');
        iframe.src = `${CONFIG.serviceUrl}/api/viewer/embed?document_token=${CONFIG.documentToken}&user_email=${encodeURIComponent(CONFIG.userEmail)}`;
        iframe.style.cssText = 'width: 100%; height: ' + CONFIG.height + '; border: none; min-height: 600px;';
        iframe.setAttribute('allowfullscreen', '');
        iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-popups allow-forms');
        
        container.innerHTML = '<div style="padding: 50px; text-align: center; color: #666;">Загрузка документа...</div>';
        
        iframe.onload = function() {
            container.innerHTML = '';
            container.appendChild(iframe);
        };
        
        iframe.onerror = function() {
            container.innerHTML = '<div style="padding: 50px; text-align: center; color: #d32f2f;">Ошибка загрузки документа</div>';
        };
        
        container.appendChild(iframe);
    })();
    </script>
</body>
</html>
```
