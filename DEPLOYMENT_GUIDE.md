# Руководство по быстрому деплою на VPS

## 🚀 Варианты деплоя (от простого к продвинутому)

---

## Вариант 1: Автоматический скрипт (Самый быстрый) ⭐

### Использование:

```bash
# В PowerShell или Git Bash
bash deploy.sh 89.110.111.184 root
```

**Что делает:**
- ✅ Копирует все файлы (кроме .git, .env, data/)
- ✅ Пересобирает backend контейнер
- ✅ Перезапускает сервис
- ✅ Показывает статус

**Время:** ~1-2 минуты

---

## Вариант 2: Rsync (Рекомендуется для частых обновлений) 🔄

### Настройка (один раз):

Создайте файл `deploy-rsync.sh`:

```bash
#!/bin/bash
rsync -avz --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'data/' \
    --exclude '*.db' \
    D:/WORK/secure-content-service/ \
    root@89.110.111.184:~/projects/secure-content-service/

ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose build backend && docker-compose restart backend"
```

**Использование:**
```bash
bash deploy-rsync.sh
```

**Преимущества:**
- ✅ Копирует только измененные файлы
- ✅ Быстрее при повторных деплоях
- ✅ Можно настроить исключения

---

## Вариант 3: SCP (Простой способ) 📦

### Для одного файла:

```powershell
# PowerShell
scp D:\WORK\secure-content-service\backend\app\api\viewer.py root@89.110.111.184:~/projects/secure-content-service/backend/app/api/
```

### Для всей папки:

```powershell
scp -r D:\WORK\secure-content-service\backend root@89.110.111.184:~/projects/secure-content-service/
```

**Затем на VPS:**
```bash
cd ~/projects/secure-content-service
docker-compose restart backend
```

---

## Вариант 4: Git (Для команды разработчиков) 👥

### Настройка (один раз):

**На VPS:**
```bash
cd ~/projects/secure-content-service
git remote add origin https://github.com/YOUR_USERNAME/secure-content-service.git
```

**На вашем компьютере:**
```bash
cd D:\WORK\secure-content-service
git push origin master
```

**На VPS после изменений:**
```bash
cd ~/projects/secure-content-service
git pull origin master
docker-compose build backend
docker-compose restart backend
```

**Преимущества:**
- ✅ Версионирование
- ✅ История изменений
- ✅ Работа в команде

---

## Вариант 5: VS Code Remote SSH (Редактирование прямо на VPS) 💻

### Настройка:

1. Установите расширение "Remote - SSH" в VS Code
2. Нажмите `F1` → "Remote-SSH: Connect to Host"
3. Выберите `root@89.110.111.184`
4. Откройте папку: `~/projects/secure-content-service`

**Теперь:**
- ✅ Редактируйте файлы прямо на VPS
- ✅ Изменения сохраняются сразу
- ✅ Перезапускайте через терминал в VS Code

**Перезапуск после изменений:**
```bash
docker-compose restart backend
```

---

## ⚡ Быстрые команды для разных случаев

### Обновить только один файл:

```powershell
# Скопировать файл
scp D:\WORK\secure-content-service\backend\app\api\viewer.py root@89.110.111.184:~/projects/secure-content-service/backend/app/api/

# Перезапустить (на VPS)
ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose restart backend"
```

### Обновить только frontend:

```powershell
scp -r D:\WORK\secure-content-service\frontend root@89.110.111.184:~/projects/secure-content-service/
ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose restart backend"
```

### Полный пересбор:

```powershell
# Скопировать все
scp -r D:\WORK\secure-content-service\* root@89.110.111.184:~/projects/secure-content-service/

# Пересобрать и перезапустить (на VPS)
ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose build && docker-compose up -d"
```

---

## 📋 Чеклист быстрого деплоя

1. **Внесли изменения локально** ✅
2. **Запустили скрипт деплоя** (`bash deploy.sh`)
3. **Проверили логи** (если нужно):
   ```bash
   ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose logs -f backend"
   ```
4. **Проверили работу** в браузере

---

## 🎯 Рекомендации

### Для быстрой разработки:
- Используйте **VS Code Remote SSH** - редактируйте прямо на VPS
- Или **rsync** - быстрая синхронизация изменений

### Для продакшн деплоя:
- Используйте **Git** - версионирование и откат изменений
- Или **автоматический скрипт** - быстрый и надежный

### Для одного файла:
- Используйте **SCP** - самый простой способ

---

## 🔧 Настройка SSH для удобства

### Создайте файл `~/.ssh/config`:

```
Host vps
    HostName 89.110.111.184
    User root
    Port 22
```

**Теперь можно подключаться просто:**
```bash
ssh vps
```

**И в скриптах использовать:**
```bash
bash deploy.sh vps root
```

---

## 💡 Полезные алиасы (опционально)

Добавьте в `~/.bashrc` или `~/.zshrc`:

```bash
# Быстрый деплой
alias deploy='bash ~/projects/secure-content-service/deploy.sh'

# Подключение к VPS
alias vps='ssh root@89.110.111.184'

# Логи backend
alias logs='ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose logs -f backend"'
```

**Использование:**
```bash
deploy
vps
logs
```

---

## ✅ Готово!

Выберите удобный для вас способ и настройте его один раз. После этого деплой будет занимать секунды!
