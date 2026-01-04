# Интеграция с Tilda - Обновленная версия

## Передача email пользователя для водяных знаков

Теперь система поддерживает передачу email пользователя из личного кабинета Tilda для отображения в водяных знаках.

### Вариант 1: Использование `/api/viewer/token`

```javascript
// В коде страницы Tilda
const userEmail = 'user@example.com'; // Получаем из личного кабинета Tilda
const documentToken = 'YOUR_DOCUMENT_TOKEN';

fetch('https://your-service.com/api/viewer/token', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        document_token: documentToken,
        user_email: userEmail  // Опционально - для водяных знаков
    })
})
.then(response => response.json())
.then(data => {
    const viewerUrl = `https://your-service.com/viewer?token=${data.viewer_token}`;
    // Встраиваем viewer
});
```

### Вариант 2: Использование `/api/viewer/embed`

```html
<!-- В HTML блоке Tilda -->
<iframe 
    src="https://your-service.com/api/viewer/embed?document_token=YOUR_TOKEN&user_email=USER_EMAIL"
    width="100%" 
    height="600px"
    frameborder="0">
</iframe>
```

Где `USER_EMAIL` - email пользователя из личного кабинета Tilda (можно получить через JavaScript).

### Пример получения email из Tilda

```javascript
// Если Tilda передает email через переменную
const userEmail = window.TildaUserEmail || localStorage.getItem('user_email');

// Или через API Tilda (если доступно)
// const userEmail = await getTildaUserEmail();

// Используем в embed URL
const embedUrl = `https://your-service.com/api/viewer/embed?document_token=${documentToken}&user_email=${encodeURIComponent(userEmail)}`;
```

## Важно

- `user_email` - **опциональный** параметр
- Если не передан, водяные знаки будут использовать только IP адрес и другую доступную информацию
- Email автоматически создается в системе при первом использовании (для водяных знаков)
- Проверка referer все еще работает для защиты от прямого доступа
