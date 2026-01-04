#!/bin/bash
# Скрипт для автоматического деплоя проекта на VPS
# Использование: bash deploy-to-vps.sh VPS_IP [VPS_USER]
# Пример: bash deploy-to-vps.sh 89.110.111.184 root

set -e

VPS_IP="${1:-89.110.111.184}"
VPS_USER="${2:-root}"
PROJECT_DIR="secure-content-service"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

if [ -z "$1" ]; then
    info "Использование: bash deploy-to-vps.sh VPS_IP [VPS_USER]"
    info "Пример: bash deploy-to-vps.sh 89.110.111.184 root"
    exit 1
fi

info "Деплой проекта на VPS: ${VPS_USER}@${VPS_IP}"

# Проверка подключения
info "Проверка подключения к VPS..."
if ! ssh -o ConnectTimeout=5 "${VPS_USER}@${VPS_IP}" "echo 'Connected'" > /dev/null 2>&1; then
    error "Не удалось подключиться к VPS. Проверьте IP адрес и SSH доступ."
    exit 1
fi

# Копирование проекта
info "Копирование проекта на VPS..."
rsync -avz --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'data/' \
    --exclude '*.db' \
    ./ "${VPS_USER}@${VPS_IP}:~/projects/${PROJECT_DIR}/"

info "Проект скопирован на VPS"

# Настройка проекта на VPS
info "Настройка проекта на VPS..."
ssh "${VPS_USER}@${VPS_IP}" << 'ENDSSH'
cd ~/projects/secure-content-service

# Создать .env если его нет
if [ ! -f .env ]; then
    cp env.example .env
    echo "Создан файл .env из env.example"
    echo "ВАЖНО: Отредактируйте .env файл перед запуском!"
fi

# Создать необходимые директории
mkdir -p data
mkdir -p static_watermarks

# Установить права
chmod +x setup-vps.sh 2>/dev/null || true

echo "Настройка завершена"
ENDSSH

info "✅ Деплой завершен!"
echo ""
echo "Следующие шаги на VPS:"
echo "1. Подключитесь: ssh ${VPS_USER}@${VPS_IP}"
echo "2. Перейдите: cd ~/projects/${PROJECT_DIR}"
echo "3. Отредактируйте .env: nano .env"
echo "4. Запустите: docker-compose build && docker-compose up -d"
echo "5. Проверьте логи: docker-compose logs -f backend"
