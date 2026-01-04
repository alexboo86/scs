#!/bin/bash
# Скрипт для настройки домена и SSL на VPS
# Использование: bash setup-domain.sh DOMAIN
# Пример: bash setup-domain.sh lessons.incrypto.ru

set -e

DOMAIN="${1:-lessons.incrypto.ru}"
BACKEND_PORT=8000

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

if [ "$EUID" -ne 0 ]; then 
    error "Пожалуйста, запустите скрипт от имени root: sudo bash setup-domain.sh $DOMAIN"
    exit 1
fi

if [ -z "$1" ]; then
    error "Укажите домен: bash setup-domain.sh lessons.incrypto.ru"
    exit 1
fi

info "Настройка домена: $DOMAIN"

# Шаг 1: Установка Nginx
info "Шаг 1: Установка Nginx..."
if command -v nginx &> /dev/null; then
    warn "Nginx уже установлен"
else
    apt update -qq
    apt install -y nginx > /dev/null 2>&1
    info "Nginx установлен"
fi

# Шаг 2: Создание конфигурации Nginx
info "Шаг 2: Создание конфигурации Nginx..."
cat > /etc/nginx/sites-available/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Логи
    access_log /var/log/nginx/${DOMAIN}_access.log;
    error_log /var/log/nginx/${DOMAIN}_error.log;

    # Увеличение размера загружаемых файлов
    client_max_body_size 50M;

    # Проксирование на backend
    location / {
        proxy_pass http://localhost:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Таймауты для больших файлов
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:$BACKEND_PORT/health;
        access_log off;
    }
}
EOF

# Активировать конфигурацию
if [ -L /etc/nginx/sites-enabled/$DOMAIN ]; then
    warn "Конфигурация уже активирована"
else
    ln -s /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
    info "Конфигурация активирована"
fi

# Проверить конфигурацию
info "Проверка конфигурации Nginx..."
if nginx -t > /dev/null 2>&1; then
    info "Конфигурация корректна"
else
    error "Ошибка в конфигурации Nginx!"
    nginx -t
    exit 1
fi

# Перезагрузить Nginx
systemctl reload nginx
info "Nginx перезагружен"

# Шаг 3: Установка Certbot для SSL
info "Шаг 3: Установка Certbot..."
if command -v certbot &> /dev/null; then
    warn "Certbot уже установлен"
else
    apt install -y certbot python3-certbot-nginx > /dev/null 2>&1
    info "Certbot установлен"
fi

# Шаг 4: Получение SSL сертификата
info "Шаг 4: Получение SSL сертификата..."
info "Certbot запросит ваш email и согласие с условиями"
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@incrypto.ru --redirect

if [ $? -eq 0 ]; then
    info "✅ SSL сертификат успешно установлен!"
else
    warn "Не удалось автоматически установить SSL. Попробуйте вручную:"
    warn "certbot --nginx -d $DOMAIN"
fi

# Шаг 5: Настройка автообновления сертификата
info "Шаг 5: Настройка автообновления сертификата..."
systemctl enable certbot.timer
systemctl start certbot.timer

echo ""
info "✅ Настройка домена завершена!"
echo ""
echo "Домен: https://$DOMAIN"
echo ""
echo "ВАЖНО: Обновите файл .env:"
echo "  ALLOWED_ORIGINS=https://$DOMAIN,http://$DOMAIN"
echo "  ALLOWED_EMBED_DOMAINS=your-tilda-domain.com"
echo ""
echo "После обновления .env перезапустите контейнер:"
echo "  cd ~/projects/secure-content-service"
echo "  docker-compose restart backend"
echo ""
