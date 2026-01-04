# Настройка HTTPS для сервера

## Проблема

Tilda использует HTTPS, а ваш сервер работает по HTTP. Браузеры блокируют загрузку HTTP контента с HTTPS страниц (Mixed Content).

## Решение: Настройка HTTPS

### Вариант 1: Cloudflare Tunnel (самый простой, рекомендуется)

1. **Установите Cloudflare Tunnel:**
   ```bash
   # На Ubuntu/Debian
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
   chmod +x /usr/local/bin/cloudflared
   ```

2. **Авторизуйтесь:**
   ```bash
   cloudflared tunnel login
   ```

3. **Создайте туннель:**
   ```bash
   cloudflared tunnel create secure-content
   ```

4. **Настройте туннель:**
   Создайте файл `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: /root/.cloudflared/<tunnel-id>.json
   
   ingress:
     - hostname: secure-content.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```

5. **Запустите туннель:**
   ```bash
   cloudflared tunnel run secure-content
   ```

6. **Обновите код на Tilda:**
   Замените `http://185.88.159.33:8000` на `https://secure-content.yourdomain.com`

### Вариант 2: Nginx + Let's Encrypt (классический способ)

1. **Установите Nginx и Certbot:**
   ```bash
   sudo apt update
   sudo apt install nginx certbot python3-certbot-nginx
   ```

2. **Настройте домен:**
   - Укажите A-запись вашего домена на IP `185.88.159.33`
   - Например: `secure-content.yourdomain.com` → `185.88.159.33`

3. **Получите SSL сертификат:**
   ```bash
   sudo certbot --nginx -d secure-content.yourdomain.com
   ```

4. **Настройте Nginx:**
   Используйте файл `nginx.conf` из проекта или создайте конфиг:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name secure-content.yourdomain.com;
       
       ssl_certificate /etc/letsencrypt/live/secure-content.yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/secure-content.yourdomain.com/privkey.pem;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

5. **Обновите код на Tilda:**
   Замените `http://185.88.159.33:8000` на `https://secure-content.yourdomain.com`

### Вариант 3: Самоподписанный сертификат (только для тестирования)

**ВНИМАНИЕ:** Браузеры будут показывать предупреждение о небезопасном соединении!

1. **Создайте самоподписанный сертификат:**
   ```bash
   sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout /etc/ssl/private/nginx-selfsigned.key \
     -out /etc/ssl/certs/nginx-selfsigned.crt
   ```

2. **Настройте Nginx** с этим сертификатом

3. **В браузере** нужно будет принять предупреждение о небезопасном сертификате

## После настройки HTTPS

1. **Обновите `.env` файл:**
   ```bash
   ALLOWED_ORIGINS=https://secure-content.yourdomain.com,https://incrypto.tilda.ws
   ```

2. **Обновите код на Tilda:**
   Замените `http://185.88.159.33:8000` на `https://secure-content.yourdomain.com`

3. **Перезапустите backend:**
   ```bash
   docker-compose restart backend
   ```

## Быстрая проверка

После настройки HTTPS проверьте:
```bash
curl https://secure-content.yourdomain.com/health
```

Должно вернуть: `{"status":"ok"}`
