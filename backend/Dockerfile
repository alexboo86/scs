FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libreoffice \
    imagemagick \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p uploads cache data static_watermarks

# Создание директории для шаблонов если её нет
RUN mkdir -p ../frontend/templates || true

# Открытие порта
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения с автоперезагрузкой (для разработки)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
