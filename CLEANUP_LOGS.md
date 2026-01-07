# Очистка логов на сервере

Если на сервере закончилось место из-за логов, выполните следующие команды:

## Вариант 1: Автоматическая очистка через скрипт

```bash
# Подключитесь к серверу по SSH
ssh root@185.88.159.33

# Загрузите скрипт на сервер (или создайте его вручную)
# Затем запустите:
bash cleanup-logs-server.sh
```

## Вариант 2: Ручная очистка (пошагово)

### 1. Проверка свободного места

```bash
df -h /
```

### 2. Очистка логов Docker контейнеров

```bash
# Очистить все логи Docker контейнеров
find /var/lib/docker/containers/ -name '*-json.log' -exec truncate -s 0 {} \;
```

### 3. Очистка системных логов

```bash
# Очистить journald логи (оставить только последние 100MB)
journalctl --vacuum-size=100M

# Или удалить логи старше 1 дня
journalctl --vacuum-time=1d

# Очистить отдельные файлы логов
truncate -s 0 /var/log/syslog
truncate -s 0 /var/log/messages
truncate -s 0 /var/log/kern.log
truncate -s 0 /var/log/auth.log
truncate -s 0 /var/log/daemon.log
```

### 4. Очистка логов Nginx

```bash
truncate -s 0 /var/log/nginx/access.log
truncate -s 0 /var/log/nginx/error.log
truncate -s 0 /var/log/nginx/access.log.1
truncate -s 0 /var/log/nginx/error.log.1
```

### 5. Удаление старых ротированных логов

```bash
# Удалить старые логи (старше 7 дней)
find /var/log -name '*.log.*' -type f -mtime +7 -delete
find /var/log -name '*.gz' -type f -mtime +7 -delete
```

### 6. Очистка временных файлов

```bash
rm -rf /tmp/*
rm -rf /var/tmp/*
```

### 7. Очистка кеша пакетов

```bash
apt-get clean
# или для CentOS/RHEL:
# yum clean all
```

## Проверка результатов

```bash
# Проверить свободное место
df -h /

# Найти самые большие директории
du -h / | sort -rh | head -10
```

## Дополнительная очистка Docker (если место все еще заканчивается)

Если `/var/lib/docker` занимает много места (как в вашем случае - 7.1G), выполните:

```bash
# Удалить остановленные контейнеры
docker container prune -f

# Удалить неиспользуемые образы
docker image prune -a -f

# Удалить неиспользуемые volumes
docker volume prune -f

# Полная очистка (удалит ВСЕ неиспользуемые ресурсы)
docker system prune -a --volumes -f
```

**Внимание:** Последняя команда удалит все неиспользуемые образы, контейнеры, volumes и сети. Убедитесь, что вам не нужны остановленные контейнеры или старые образы.

## Дополнительная очистка (если место все еще заканчивается)

### Очистка базы данных

```bash
# Очистить старые сессии просмотра
docker exec secure-content-backend python cleanup_old_sessions.py
```

### Очистка кеша приложения

```bash
# Проверить размер кеша
docker exec secure-content-backend du -sh /app/cache

# Удалить старые файлы кеша (старше 30 дней)
docker exec secure-content-backend find /app/cache -type f -mtime +30 -delete
```

### Очистка загруженных файлов

```bash
# Проверить размер uploads
docker exec secure-content-backend du -sh /app/uploads

# Удалить старые файлы (если нужно)
docker exec secure-content-backend find /app/uploads -type f -mtime +90 -delete
```

## Настройка автоматической очистки логов

Для предотвращения переполнения в будущем, можно настроить ротацию логов:

### Docker daemon.json

Создайте или отредактируйте `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Затем перезапустите Docker:
```bash
systemctl restart docker
```

### Nginx log rotation

Убедитесь, что `/etc/logrotate.d/nginx` настроен правильно:

```
/var/log/nginx/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```
