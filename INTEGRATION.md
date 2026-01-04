# Интеграция Secure Content Service

## Встраивание через iframe

### Базовый пример

```html
<!DOCTYPE html>
<html>
<head>
    <title>Моя онлайн школа</title>
</head>
<body>
    <h1>Личный кабинет</h1>
    
    <!-- Встраивание защищенного контента -->
    <iframe 
        id="secureContentFrame"
        src="https://your-content-service.com/viewer?token=VIEWER_TOKEN"
        width="100%"
        height="800px"
        frameborder="0"
        allowfullscreen>
    </iframe>
    
    <script>
        // Получение токена для просмотра
        async function loadSecureContent(documentToken, userEmail) {
            try {
                // 1. Получаем viewer token от вашего API
                const response = await fetch('https://your-content-service.com/api/viewer/token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        document_token: documentToken,
                        user_email: userEmail
                    })
                });
                
                const data = await response.json();
                
                // 2. Загружаем viewer в iframe
                const iframe = document.getElementById('secureContentFrame');
                iframe.src = `https://your-content-service.com/viewer?token=${data.viewer_token}`;
                
            } catch (error) {
                console.error('Ошибка загрузки контента:', error);
            }
        }
        
        // Использование
        loadSecureContent('DOCUMENT_ACCESS_TOKEN', 'user@example.com');
    </script>
</body>
</html>
```

## Интеграция с вашим сайтом

### Вариант 1: Прямая интеграция через API

```javascript
// В вашем личном кабинете
class SecureContentViewer {
    constructor(apiBase, userEmail) {
        this.apiBase = apiBase;
        this.userEmail = userEmail;
    }
    
    async loadDocument(documentToken) {
        // Получаем viewer token
        const tokenResponse = await fetch(`${this.apiBase}/api/viewer/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_token: documentToken,
                user_email: this.userEmail
            })
        });
        
        const { viewer_token } = await tokenResponse.json();
        
        // Возвращаем URL для iframe
        return `${this.apiBase}/viewer?token=${viewer_token}`;
    }
}

// Использование
const viewer = new SecureContentViewer(
    'https://your-content-service.com',
    'user@example.com'
);

const viewerUrl = await viewer.loadDocument('DOCUMENT_TOKEN');
document.getElementById('iframe').src = viewerUrl;
```

### Вариант 2: Интеграция через ваш backend

```python
# В вашем backend (Python пример)
import requests

def get_viewer_url(document_token, user_email):
    """Получение URL для просмотра документа"""
    response = requests.post(
        'https://your-content-service.com/api/viewer/token',
        json={
            'document_token': document_token,
            'user_email': user_email
        }
    )
    data = response.json()
    return f"https://your-content-service.com/viewer?token={data['viewer_token']}"

# В шаблоне
viewer_url = get_viewer_url(document_token, current_user.email)
```

## API Endpoints

### 1. Создание токена для просмотра

```http
POST /api/viewer/token
Content-Type: application/json

{
    "document_token": "document_access_token",
    "user_email": "user@example.com"
}
```

**Ответ:**
```json
{
    "viewer_token": "viewer_session_token",
    "viewer_url": "/viewer?token=viewer_session_token",
    "expires_at": "2024-01-01T12:00:00"
}
```

### 2. Получение изображения страницы

```http
GET /api/documents/{document_id}/page/{page_number}?viewer_token={viewer_token}
```

**Ответ:** Изображение PNG

### 3. Загрузка документа

```http
POST /api/documents/upload
Content-Type: multipart/form-data

file: [PDF/PPT файл]
name: "Название документа"
watermark_settings: "{json настройки}"
```

## Настройка CORS

В файле `.env` укажите разрешенные домены:

```env
ALLOWED_ORIGINS=https://your-school.com,https://www.your-school.com
```

## Безопасность

1. **Токены доступа** имеют ограниченный срок действия (по умолчанию 24 часа)
2. **HTTPS обязателен** в продакшене
3. **Проверка доступа** выполняется на сервере перед выдачей токена
4. **IP адрес** фиксируется при создании сессии просмотра

## Примеры для разных фреймворков

### React

```jsx
import { useEffect, useState } from 'react';

function SecureContentViewer({ documentToken, userEmail }) {
    const [viewerUrl, setViewerUrl] = useState(null);
    
    useEffect(() => {
        async function loadViewer() {
            const response = await fetch('/api/viewer/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    document_token: documentToken,
                    user_email: userEmail
                })
            });
            const data = await response.json();
            setViewerUrl(data.viewer_url);
        }
        loadViewer();
    }, [documentToken, userEmail]);
    
    if (!viewerUrl) return <div>Загрузка...</div>;
    
    return (
        <iframe
            src={viewerUrl}
            width="100%"
            height="800px"
            frameBorder="0"
            allowFullScreen
        />
    );
}
```

### Vue.js

```vue
<template>
    <iframe
        v-if="viewerUrl"
        :src="viewerUrl"
        width="100%"
        height="800px"
        frameborder="0"
    />
    <div v-else>Загрузка...</div>
</template>

<script>
export default {
    data() {
        return {
            viewerUrl: null
        };
    },
    async mounted() {
        const response = await fetch('/api/viewer/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_token: this.documentToken,
                user_email: this.userEmail
            })
        });
        const data = await response.json();
        this.viewerUrl = data.viewer_url;
    },
    props: ['documentToken', 'userEmail']
};
</script>
```

## Мобильная поддержка

Viewer автоматически адаптируется под мобильные устройства. Для лучшего опыта добавьте:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
```

## Обработка ошибок

```javascript
async function loadSecureContent(documentToken, userEmail) {
    try {
        const response = await fetch('/api/viewer/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_token: documentToken,
                user_email: userEmail
            })
        });
        
        if (!response.ok) {
            if (response.status === 403) {
                alert('Доступ запрещен');
                return;
            }
            if (response.status === 404) {
                alert('Документ не найден');
                return;
            }
            throw new Error('Ошибка сервера');
        }
        
        const data = await response.json();
        // Загружаем viewer
        document.getElementById('iframe').src = data.viewer_url;
        
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Не удалось загрузить контент');
    }
}
```
