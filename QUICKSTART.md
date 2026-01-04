# Быстрый старт

## 1. Установка и запуск

### Через Docker Compose (рекомендуется)

```bash
# Клонируйте репозиторий
cd secure-content-service

# Создайте файл .env на основе env.example
cp env.example .env

# Отредактируйте .env и укажите свои настройки
# Особенно важно изменить SECRET_KEY!

# Запустите сервис
docker-compose up -d

# Проверьте статус
docker-compose ps

# Просмотрите логи
docker-compose logs -f backend
```

Сервис будет доступен на `http://localhost:8000`

### Локальная установка

```bash
# Установите зависимости
cd backend
pip install -r requirements.txt

# Установите системные зависимости
# Ubuntu/Debian:
sudo apt-get install poppler-utils libreoffice imagemagick

# macOS:
brew install poppler libreoffice imagemagick

# Windows:
# Скачайте и установите:
# - Poppler: https://github.com/oschwartz10612/poppler-windows/releases
# - LibreOffice: https://www.libreoffice.org/download/

# Инициализируйте базу данных
python -m app.utils.init_db

# Запустите сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2. Первоначальная настройка

### Создание администратора

```bash
# Через API
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@school.com",
    "name": "Администратор"
  }'
```

### Загрузка первого документа

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@presentation.pdf" \
  -F "name=Моя презентация" \
  -F "watermark_settings={\"custom_text\":\"Моя школа\",\"opacity\":0.25}"
```

Ответ содержит `access_token` - используйте его для предоставления доступа.

### Предоставление доступа пользователю

```bash
# Сначала создайте пользователя
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@school.com",
    "name": "Студент"
  }'

# Предоставьте доступ к документу
curl -X POST http://localhost:8000/api/admin/documents/1/access \
  -F "user_emails=student@school.com"
```

## 3. Использование viewer

### Получение токена для просмотра

```bash
curl -X POST http://localhost:8000/api/viewer/token \
  -H "Content-Type: application/json" \
  -d '{
    "document_token": "ACCESS_TOKEN_ИЗ_ЗАГРУЗКИ",
    "user_email": "student@school.com"
  }'
```

Ответ содержит `viewer_token` и `viewer_url`.

### Открытие viewer

Откройте в браузере:
```
http://localhost:8000/viewer?token=VIEWER_TOKEN
```

Или встройте в iframe:

```html
<iframe 
    src="http://localhost:8000/viewer?token=VIEWER_TOKEN"
    width="100%"
    height="800px"
    frameborder="0">
</iframe>
```

## 4. Интеграция в ваш сайт

См. подробную документацию в `INTEGRATION.md`

## 5. API Документация

После запуска сервиса доступна интерактивная документация:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Структура директорий

```
secure-content-service/
├── backend/
│   ├── app/              # Код приложения
│   ├── uploads/          # Загруженные файлы (создается автоматически)
│   ├── cache/            # Кеш изображений (создается автоматически)
│   ├── data/             # База данных (создается автоматически)
│   └── static_watermarks/ # Статические водяные знаки (логотипы)
├── frontend/
│   └── templates/        # HTML шаблоны
└── docker-compose.yml
```

## Настройка статических водяных знаков

1. Поместите логотип школы в `backend/static_watermarks/logo.png`
2. При загрузке документа укажите `static_watermark_id` в настройках

## Безопасность

⚠️ **ВАЖНО для продакшена:**

1. Измените `SECRET_KEY` в `.env`
2. Используйте HTTPS
3. Настройте `ALLOWED_ORIGINS` для ваших доменов
4. Регулярно обновляйте зависимости
5. Используйте сильные пароли для БД (если используете PostgreSQL/MySQL)

## Troubleshooting

### Ошибка конвертации PDF

Убедитесь, что установлен `poppler-utils`:
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# Проверка
pdftoppm -h
```

### Ошибка конвертации PPT

Убедитесь, что установлен `libreoffice`:
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice

# Проверка
libreoffice --version
```

### Проблемы с правами доступа

```bash
# Убедитесь, что директории доступны для записи
chmod -R 755 backend/uploads backend/cache backend/data
```

## Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs backend`
2. Проверьте документацию API: `http://localhost:8000/docs`
3. Убедитесь, что все зависимости установлены
