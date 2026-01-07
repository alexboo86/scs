#!/bin/bash
# Скрипт для очистки Docker ресурсов (образы, контейнеры, volumes)
# Запуск: bash cleanup-docker.sh

echo "============================================================"
echo "  Docker Resources Cleanup"
echo "============================================================"

# Проверка свободного места ДО очистки
echo ""
echo "[INFO] Checking disk space BEFORE cleanup..."
df -h /

# Проверка размера Docker директории
echo ""
echo "[INFO] Docker directory size:"
du -sh /var/lib/docker 2>/dev/null || echo "Could not check Docker directory"

# 1. Удаление остановленных контейнеров
echo ""
echo "[INFO] Removing stopped containers..."
docker container prune -f
if [ $? -eq 0 ]; then
    echo "[INFO] Stopped containers removed"
else
    echo "[WARN] Could not remove stopped containers"
fi

# 2. Удаление неиспользуемых образов
echo ""
echo "[INFO] Removing unused images..."
docker image prune -a -f
if [ $? -eq 0 ]; then
    echo "[INFO] Unused images removed"
else
    echo "[WARN] Could not remove unused images"
fi

# 3. Удаление неиспользуемых volumes
echo ""
echo "[INFO] Removing unused volumes..."
docker volume prune -f
if [ $? -eq 0 ]; then
    echo "[INFO] Unused volumes removed"
else
    echo "[WARN] Could not remove unused volumes"
fi

# 4. Удаление неиспользуемых сетей
echo ""
echo "[INFO] Removing unused networks..."
docker network prune -f
if [ $? -eq 0 ]; then
    echo "[INFO] Unused networks removed"
else
    echo "[WARN] Could not remove unused networks"
fi

# 5. Полная очистка системы Docker (все неиспользуемые ресурсы)
echo ""
echo "[INFO] Performing full Docker system cleanup..."
echo "[WARN] This will remove ALL unused containers, networks, images, and build cache"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker system prune -a --volumes -f
    if [ $? -eq 0 ]; then
        echo "[INFO] Docker system cleaned"
    else
        echo "[WARN] Could not clean Docker system"
    fi
else
    echo "[INFO] Skipped full cleanup"
fi

# Проверка размера Docker директории после очистки
echo ""
echo "[INFO] Docker directory size AFTER cleanup:"
du -sh /var/lib/docker 2>/dev/null || echo "Could not check Docker directory"

# Проверка свободного места ПОСЛЕ очистки
echo ""
echo "[INFO] Checking disk space AFTER cleanup..."
df -h /

echo ""
echo "============================================================"
echo "  Docker cleanup complete!"
echo "============================================================"
