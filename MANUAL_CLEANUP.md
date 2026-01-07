# Ручная очистка базы данных

Если база данных переполнена, выполните следующие шаги:

## Вариант 1: Через Docker (рекомендуется)

```bash
# Подключитесь к серверу по SSH
ssh root@185.88.159.33

# Запустите скрипт очистки
docker exec secure-content-backend python cleanup_old_sessions.py
```

## Вариант 2: Через SQLite напрямую

```bash
# Подключитесь к серверу по SSH
ssh root@185.88.159.33

# Найдите путь к базе данных
docker exec secure-content-backend ls -lh /app/data/database.db

# Подключитесь к базе данных
docker exec -it secure-content-backend sqlite3 /app/data/database.db

# Удалите старые сессии (старше 7 дней)
DELETE FROM viewing_sessions WHERE created_at < datetime('now', '-7 days');

# Оптимизируйте базу данных
VACUUM;

# Выйдите
.quit
```

## Вариант 3: Проверка размера диска

```bash
# Проверьте свободное место на диске
df -h /

# Проверьте размер базы данных
docker exec secure-content-backend ls -lh /app/data/database.db

# Проверьте размер директорий
docker exec secure-content-backend du -sh /app/data /app/cache /app/uploads
```

## Автоматическая очистка

После деплоя обновленного кода, старые сессии будут автоматически удаляться при создании новых сессий (старше 7 дней).
