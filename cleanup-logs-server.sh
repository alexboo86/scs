#!/bin/bash
# Скрипт для очистки всех логов на сервере
# Запуск: bash cleanup-logs-server.sh

echo "============================================================"
echo "  Server Logs Cleanup"
echo "============================================================"

# Проверка свободного места ДО очистки
echo ""
echo "[INFO] Checking disk space BEFORE cleanup..."
df -h /

# 1. Очистка логов Docker контейнеров
echo ""
echo "[INFO] Cleaning Docker container logs..."
find /var/lib/docker/containers/ -name '*-json.log' -exec truncate -s 0 {} \; 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[INFO] Docker container logs cleared"
else
    echo "[WARN] Could not clear Docker logs"
fi

# 2. Очистка системных логов
echo ""
echo "[INFO] Cleaning system logs..."
journalctl --vacuum-time=1d 2>/dev/null
journalctl --vacuum-size=100M 2>/dev/null
truncate -s 0 /var/log/syslog 2>/dev/null || true
truncate -s 0 /var/log/messages 2>/dev/null || true
truncate -s 0 /var/log/kern.log 2>/dev/null || true
truncate -s 0 /var/log/auth.log 2>/dev/null || true
truncate -s 0 /var/log/daemon.log 2>/dev/null || true
echo "[INFO] System logs cleared"

# 3. Очистка логов Nginx
echo ""
echo "[INFO] Cleaning Nginx logs..."
truncate -s 0 /var/log/nginx/access.log 2>/dev/null || true
truncate -s 0 /var/log/nginx/error.log 2>/dev/null || true
truncate -s 0 /var/log/nginx/access.log.1 2>/dev/null || true
truncate -s 0 /var/log/nginx/error.log.1 2>/dev/null || true
echo "[INFO] Nginx logs cleared"

# 4. Очистка старых ротированных логов
echo ""
echo "[INFO] Cleaning old rotated logs..."
find /var/log -name '*.log.*' -type f -mtime +7 -delete 2>/dev/null || true
find /var/log -name '*.gz' -type f -mtime +7 -delete 2>/dev/null || true
echo "[INFO] Old rotated logs cleaned"

# 5. Очистка временных файлов
echo ""
echo "[INFO] Cleaning temporary files..."
rm -rf /tmp/* 2>/dev/null || true
rm -rf /var/tmp/* 2>/dev/null || true
echo "[INFO] Temporary files cleaned"

# 6. Очистка кеша пакетов
echo ""
echo "[INFO] Cleaning package cache..."
apt-get clean 2>/dev/null || yum clean all 2>/dev/null || true
echo "[INFO] Package cache cleaned"

# 7. Очистка Docker ресурсов (образы, контейнеры, volumes)
echo ""
echo "[INFO] Cleaning Docker resources..."
echo "[INFO] Removing stopped containers..."
docker container prune -f 2>/dev/null || true

echo "[INFO] Removing unused images..."
docker image prune -a -f 2>/dev/null || true

echo "[INFO] Removing unused volumes..."
docker volume prune -f 2>/dev/null || true

echo "[INFO] Removing unused networks..."
docker network prune -f 2>/dev/null || true

echo "[INFO] Performing full Docker system cleanup..."
docker system prune -a --volumes -f 2>/dev/null || true

echo "[INFO] Docker resources cleaned"

# Проверка свободного места ПОСЛЕ очистки
echo ""
echo "[INFO] Checking disk space AFTER cleanup..."
df -h /

# Показываем размер самых больших директорий
echo ""
echo "[INFO] Top 10 largest directories:"
du -h / 2>/dev/null | sort -rh | head -10

echo ""
echo "============================================================"
echo "  Cleanup complete!"
echo "============================================================"
echo ""
echo "[INFO] If disk is still full, check:"
echo "  1. Database size: docker exec secure-content-backend ls -lh /app/data/database.db"
echo "  2. Cache directory: docker exec secure-content-backend du -sh /app/cache"
echo "  3. Uploads directory: docker exec secure-content-backend du -sh /app/uploads"
echo "  4. Run database cleanup: docker exec secure-content-backend python cleanup_old_sessions.py"
