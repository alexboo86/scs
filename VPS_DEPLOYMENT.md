# Деплой на VPS и разработка через SSH

## Преимущества VPS для разработки

✅ **Единая среда** - разработка и продакшн на одном сервере  
✅ **Доступ 24/7** - работайте с любого компьютера  
✅ **SSH доступ** - полный контроль через терминал  
✅ **Git на сервере** - версионирование прямо на VPS  
✅ **Резервные копии** - легко делать бэкапы  

---

## Шаг 1: Выбор и настройка VPS

### Рекомендуемые провайдеры:
- **DigitalOcean** (от $6/мес) - простой интерфейс
- **Hetzner** (от €4/мес) - хорошее соотношение цена/качество
- **Linode** (от $5/мес) - надежный
- **Vultr** (от $6/мес) - быстрый
- **AWS Lightsail** (от $5/мес) - интеграция с AWS

### Минимальные требования:
- **RAM**: 2GB (рекомендуется 4GB)
- **CPU**: 2 ядра
- **Диск**: 20GB SSD
- **ОС**: Ubuntu 22.04 LTS (рекомендуется)

---

## Шаг 2: Первоначальная настройка VPS

### 1. Подключитесь к VPS по SSH:

```bash
ssh root@YOUR_VPS_IP
```

### 2. Создайте пользователя для разработки:

```bash
# Создать пользователя
adduser developer

# Добавить в группу sudo
usermod -aG sudo developer

# Переключиться на пользователя
su - developer
```

### 3. Настройте SSH ключи (безопаснее паролей):

**На вашем компьютере:**

```bash
# Сгенерируйте SSH ключ (если еще нет)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Скопируйте ключ на VPS
ssh-copy-id developer@YOUR_VPS_IP
```

**Или вручную:**

```bash
# Показать публичный ключ
cat ~/.ssh/id_ed25519.pub

# На VPS добавить в ~/.ssh/authorized_keys
```

### 4. Установите необходимые пакеты на VPS:

```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить базовые инструменты
sudo apt install -y git curl wget vim nano

# Установить Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установить Docker Compose (если не установлен)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перезайти в систему для применения изменений группы docker
exit
# Затем снова подключиться: ssh developer@YOUR_VPS_IP
```

---

## Шаг 3: Перенос проекта на VPS

### Вариант 1: Через Git (Рекомендуется) ⭐

**На VPS:**

```bash
# Перейти в домашнюю директорию
cd ~

# Клонировать репозиторий (если уже на GitHub)
git clone https://github.com/YOUR_USERNAME/secure-content-service.git
cd secure-content-service

# Или создать репозиторий на VPS
mkdir -p ~/projects/secure-content-service
cd ~/projects/secure-content-service
git init
```

**На вашем компьютере:**

```bash
# Добавить VPS как удаленный репозиторий
cd D:\WORK\secure-content-service
git remote add vps developer@YOUR_VPS_IP:~/projects/secure-content-service/.git

# Или через SSH URL
git remote add vps ssh://developer@YOUR_VPS_IP/~/projects/secure-content-service/.git

# Отправить код на VPS
git push vps master
```

**Или проще - через rsync:**

```bash
# С вашего компьютера
rsync -avz --exclude '.git' \
  D:\WORK\secure-content-service\ \
  developer@YOUR_VPS_IP:~/projects/secure-content-service/
```

### Вариант 2: Через SCP (простой способ)

**С вашего компьютера:**

```bash
# Скопировать всю папку на VPS
scp -r D:\WORK\secure-content-service developer@YOUR_VPS_IP:~/projects/
```

---

## Шаг 4: Настройка проекта на VPS

### 1. Создайте файл `.env`:

```bash
cd ~/projects/secure-content-service
cp env.example .env
nano .env
```

**Настройте переменные:**
```env
DATABASE_URL=sqlite:///./secure_content.db
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://YOUR_VPS_IP:8000,https://yourdomain.com
```

### 2. Запустите проект:

```bash
# Собрать и запустить контейнеры
docker-compose build
docker-compose up -d

# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs -f backend
```

### 3. Настройте файрвол:

```bash
# Разрешить порты
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Backend API
sudo ufw allow 80/tcp    # HTTP (если используете nginx)
sudo ufw allow 443/tcp   # HTTPS (если используете SSL)

# Включить файрвол
sudo ufw enable
```

---

## Шаг 5: Настройка домена (опционально)

### 1. Настройте DNS:
- Укажите A-запись вашего домена на IP VPS

### 2. Установите Nginx:

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/secure-content
```

**Конфигурация Nginx:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активировать конфигурацию
sudo ln -s /etc/nginx/sites-available/secure-content /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Установите SSL (Let's Encrypt):

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## Шаг 6: Работа через SSH

### Подключение к VPS:

```bash
ssh developer@YOUR_VPS_IP
```

### Основные команды для разработки:

```bash
# Перейти в проект
cd ~/projects/secure-content-service

# Посмотреть статус Git
git status

# Посмотреть логи
docker-compose logs -f backend

# Перезапустить сервисы
docker-compose restart backend

# Пересобрать после изменений
docker-compose build backend
docker-compose up -d backend

# Редактировать файлы (vim/nano)
nano frontend/templates/viewer.html
vim backend/app/api/viewer.py

# Создать коммит
git add .
git commit -m "Update viewer"
git push origin master
```

---

## Шаг 7: Настройка VS Code для работы через SSH

### 1. Установите расширение "Remote - SSH"

### 2. Подключитесь к VPS:

1. Нажмите `F1` → "Remote-SSH: Connect to Host"
2. Выберите `developer@YOUR_VPS_IP`
3. Откройте папку проекта: `~/projects/secure-content-service`

### 3. Теперь можете редактировать файлы прямо на VPS!

---

## Шаг 8: Автоматизация деплоя

### Создайте скрипт деплоя `deploy.sh`:

```bash
#!/bin/bash
# deploy.sh

echo "🚀 Starting deployment..."

# Перейти в директорию проекта
cd ~/projects/secure-content-service

# Получить последние изменения из Git
git pull origin master

# Пересобрать и перезапустить контейнеры
docker-compose build
docker-compose up -d

# Показать статус
docker-compose ps

echo "✅ Deployment complete!"
```

```bash
# Сделать исполняемым
chmod +x deploy.sh

# Запустить
./deploy.sh
```

---

## Шаг 9: Резервное копирование

### Создайте скрипт бэкапа `backup.sh`:

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Бэкап базы данных
docker-compose exec -T db pg_dump -U postgres > $BACKUP_DIR/db_$DATE.sql

# Бэкап файлов проекта
tar -czf $BACKUP_DIR/project_$DATE.tar.gz ~/projects/secure-content-service

# Удалить старые бэкапы (старше 7 дней)
find $BACKUP_DIR -type f -mtime +7 -delete

echo "✅ Backup created: $BACKUP_DIR"
```

```bash
chmod +x backup.sh

# Добавить в cron (ежедневно в 3:00)
crontab -e
# Добавить строку:
0 3 * * * ~/projects/secure-content-service/backup.sh
```

---

## Полезные команды

```bash
# Мониторинг ресурсов
htop
df -h  # Дисковое пространство
free -h  # Память

# Логи Docker
docker-compose logs -f
docker-compose logs backend --tail=100

# Перезапуск сервисов
docker-compose restart
docker-compose restart backend

# Остановка/запуск
docker-compose stop
docker-compose start
docker-compose down
docker-compose up -d

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Проверка портов
sudo netstat -tulpn | grep LISTEN
```

---

## Безопасность

### 1. Отключите вход по паролю (только SSH ключи):

```bash
sudo nano /etc/ssh/sshd_config
```

Найдите и измените:
```
PasswordAuthentication no
PubkeyAuthentication yes
```

```bash
sudo systemctl restart sshd
```

### 2. Измените SSH порт (опционально):

```bash
sudo nano /etc/ssh/sshd_config
# Измените Port 22 на другой (например, 2222)
sudo systemctl restart sshd
```

### 3. Настройте fail2ban:

```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Troubleshooting

### Проблема: Не могу подключиться по SSH
```bash
# Проверьте файрвол
sudo ufw status

# Проверьте SSH сервис
sudo systemctl status ssh
```

### Проблема: Docker требует sudo
```bash
# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
# Перезайти в систему
```

### Проблема: Порты заняты
```bash
# Найти процесс на порту
sudo lsof -i :8000
# Убить процесс
sudo kill -9 PID
```

---

## Готово! 🎉

Теперь у вас есть:
- ✅ VPS с проектом
- ✅ SSH доступ для разработки
- ✅ Git для версионирования
- ✅ Docker для запуска приложения
- ✅ Возможность работать с любого компьютера

**Следующие шаги:**
1. Купите VPS
2. Выполните шаги 1-4
3. Начните разработку через SSH!
