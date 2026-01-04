#!/bin/bash
# Быстрый деплой на VPS
# Использование: bash deploy.sh [VPS_IP] [VPS_USER]
# Пример: bash deploy.sh 89.110.111.184 root

set -e

VPS_IP="${1:-89.110.111.184}"
VPS_USER="${2:-root}"
PROJECT_DIR="secure-content-service"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Проверка подключения
step "Проверка подключения к VPS..."
if ! ssh -o ConnectTimeout=5 "${VPS_USER}@${VPS_IP}" "echo 'Connected'" > /dev/null 2>&1; then
    error "Не удалось подключиться к VPS. Проверьте IP адрес и SSH доступ."
    exit 1
fi
info "Подключение установлено"

# Определяем путь к проекту (Windows или Linux)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    # Windows
    PROJECT_PATH="D:/WORK/secure-content-service"
    # Используем rsync через SSH если доступен, иначе scp
    if command -v rsync &> /dev/null; then
        step "Синхронизация файлов через rsync..."
        rsync -avz --exclude '.git' \
            --exclude '__pycache__' \
            --exclude '*.pyc' \
            --exclude '.env' \
            --exclude 'data/' \
            --exclude '*.db' \
            --exclude 'node_modules/' \
            --exclude '.vscode/' \
            --exclude '*.log' \
            "${PROJECT_PATH}/" "${VPS_USER}@${VPS_IP}:~/projects/${PROJECT_DIR}/"
    else
        step "Копирование файлов через scp..."
        scp -r "${PROJECT_PATH}"/* "${VPS_USER}@${VPS_IP}:~/projects/${PROJECT_DIR}/"
    fi
else
    # Linux/Mac
    PROJECT_PATH="$(pwd)"
    step "Синхронизация файлов через rsync..."
    rsync -avz --exclude '.git' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.env' \
        --exclude 'data/' \
        --exclude '*.db' \
        --exclude 'node_modules/' \
        --exclude '.vscode/' \
        --exclude '*.log' \
        "${PROJECT_PATH}/" "${VPS_USER}@${VPS_IP}:~/projects/${PROJECT_DIR}/"
fi

info "Файлы скопированы на VPS"

# Выполняем команды на VPS
step "Пересборка и перезапуск контейнера..."
ssh "${VPS_USER}@${VPS_IP}" << ENDSSH
cd ~/projects/${PROJECT_DIR}

# Пересобрать backend
echo "🔨 Сборка backend контейнера..."
docker-compose build backend

# Перезапустить backend
echo "🔄 Перезапуск backend..."
docker-compose restart backend

# Показать статус
echo ""
echo "📊 Статус контейнеров:"
docker-compose ps

echo ""
echo "✅ Деплой завершен!"
ENDSSH

info "✅ Готово! Проект обновлен на VPS"
