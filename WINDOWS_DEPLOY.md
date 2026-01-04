# Деплой на VPS с Windows - Быстрое руководство

## 🚀 Самый быстрый способ (PowerShell скрипт)

### Использование:

```powershell
# Откройте PowerShell в папке проекта
cd D:\WORK\secure-content-service

# Запустите скрипт деплоя
.\deploy.ps1
```

**Или с параметрами:**
```powershell
.\deploy.ps1 89.110.111.184 root
```

**Что делает:**
- ✅ Копирует все файлы на VPS
- ✅ Пересобирает backend контейнер
- ✅ Перезапускает сервис
- ✅ Показывает статус

**Время:** ~1-2 минуты

---

## 📝 Для одного файла (самый простой)

### Используйте скрипт:

```powershell
.\deploy-single-file.ps1 backend\app\api\viewer.py
```

**Или вручную:**

```powershell
# Скопировать файл
scp D:\WORK\secure-content-service\backend\app\api\viewer.py root@89.110.111.184:~/projects/secure-content-service/backend/app/api/

# Перезапустить
ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose restart backend"
```

---

## 🔧 Настройка для удобства

### 1. Добавьте PowerShell в PATH (если еще нет)

Обычно PowerShell уже доступен, но если нет:
- Откройте PowerShell от имени администратора
- Выполните: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 2. Создайте алиас (опционально)

Добавьте в PowerShell профиль (`$PROFILE`):

```powershell
# Откройте профиль
notepad $PROFILE

# Добавьте строки:
function Deploy-VPS {
    param([string]$File = "")
    if ($File) {
        & "D:\WORK\secure-content-service\deploy-single-file.ps1" $File
    } else {
        & "D:\WORK\secure-content-service\deploy.ps1"
    }
}

function Connect-VPS {
    ssh root@89.110.111.184
}

function Show-Logs {
    ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose logs -f backend"
}

Set-Alias -Name deploy -Value Deploy-VPS
Set-Alias -Name vps -Value Connect-VPS
Set-Alias -Name logs -Value Show-Logs
```

**Использование:**
```powershell
deploy                    # Полный деплой
deploy backend\app\api\viewer.py  # Один файл
vps                       # Подключиться к VPS
logs                      # Показать логи
```

---

## ⚡ Быстрые команды

### Обновить только backend:

```powershell
scp -r D:\WORK\secure-content-service\backend root@89.110.111.184:~/projects/secure-content-service/
ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose build backend && docker-compose restart backend"
```

### Обновить только frontend:

```powershell
scp -r D:\WORK\secure-content-service\frontend root@89.110.111.184:~/projects/secure-content-service/
ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose restart backend"
```

### Полный пересбор:

```powershell
.\deploy.ps1
```

---

## 🎯 Рекомендации для Windows

### Для быстрой разработки:
1. **Используйте VS Code Remote SSH** - редактируйте прямо на VPS
2. **Или PowerShell скрипт** - быстрый деплой одной командой

### Для одного файла:
- Используйте `deploy-single-file.ps1` - самый простой способ

### Для полного деплоя:
- Используйте `deploy.ps1` - автоматизирует весь процесс

---

## 🔍 Troubleshooting

### Проблема: "scp не распознается"

**Решение:** Установите OpenSSH для Windows:
```powershell
# В PowerShell от имени администратора
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

### Проблема: "ssh не распознается"

**Решение:** То же самое - установите OpenSSH Client

### Проблема: "ExecutionPolicy"

**Решение:**
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## ✅ Готово!

Теперь деплой с Windows занимает секунды!
