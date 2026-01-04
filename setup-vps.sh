#!/bin/bash
# Автоматическая настройка VPS для secure-content-service
# Запустите этот скрипт на VPS: bash setup-vps.sh

set -e  # Остановить при ошибке

echo "🚀 Начинаем настройку VPS..."

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    error "Пожалуйста, запустите скрипт от имени root: sudo bash setup-vps.sh"
    exit 1
fi

info "Шаг 1: Обновление системы..."
apt update -qq
apt upgrade -y -qq

info "Шаг 2: Установка базовых инструментов..."
apt install -y git curl wget vim nano htop ufw > /dev/null 2>&1

info "Шаг 3: Создание пользователя developer..."
if id "developer" &>/dev/null; then
    warn "Пользователь developer уже существует"
else
    # Создать пользователя без интерактивного ввода
    useradd -m -s /bin/bash developer
    echo "developer:$(openssl rand -base64 32)" | chpasswd
    usermod -aG sudo developer
    info "Пользователь developer создан"
fi

info "Шаг 4: Установка Docker..."
if command -v docker &> /dev/null; then
    warn "Docker уже установлен"
else
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh > /dev/null 2>&1
    rm get-docker.sh
    info "Docker установлен"
fi

# Добавить пользователей в группу docker
usermod -aG docker root
usermod -aG docker developer

info "Шаг 5: Установка Docker Compose..."
if command -v docker-compose &> /dev/null; then
    warn "Docker Compose уже установлен"
else
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    info "Docker Compose установлен"
fi

info "Шаг 6: Настройка файрвола..."
# Разрешить SSH (важно!)
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 8000/tcp > /dev/null 2>&1
ufw allow 80/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1
echo "y" | ufw enable > /dev/null 2>&1
info "Файрвол настроен"

info "Шаг 7: Создание директории для проекта..."
mkdir -p /root/projects
mkdir -p /home/developer/projects
chown developer:developer /home/developer/projects

info "Шаг 8: Настройка прав доступа..."
# Разрешить developer работать с проектами в /root/projects
chmod 755 /root
chmod 755 /root/projects

echo ""
info "✅ Базовая настройка VPS завершена!"
echo ""
echo "Следующие шаги:"
echo "1. Скопируйте проект на VPS (через SCP или Git)"
echo "2. Перейдите в директорию проекта"
echo "3. Создайте .env файл из env.example"
echo "4. Запустите: docker-compose build && docker-compose up -d"
echo ""
echo "Для подключения к VPS используйте:"
echo "  ssh developer@$(hostname -I | awk '{print $1}')"
echo ""
