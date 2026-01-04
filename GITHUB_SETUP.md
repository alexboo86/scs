# Инструкция по загрузке проекта на GitHub

## Шаг 1: Создайте репозиторий на GitHub

1. Зайдите на https://github.com
2. Войдите в свой аккаунт (или создайте новый)
3. Нажмите кнопку **"+"** в правом верхнем углу → **"New repository"**
4. Заполните:
   - **Repository name**: `secure-content-service`
   - **Description**: `Secure content viewer service with watermark and Tilda integration`
   - **Visibility**: Private (рекомендуется) или Public
   - **НЕ** ставьте галочки на "Add a README file", "Add .gitignore", "Choose a license" (все уже есть)
5. Нажмите **"Create repository"**

## Шаг 2: Подключите локальный репозиторий к GitHub

Выполните команды в терминале (замените `YOUR_USERNAME` на ваш GitHub username):

```bash
cd D:\WORK\secure-content-service

# Подключите удаленный репозиторий
git remote add origin https://github.com/YOUR_USERNAME/secure-content-service.git

# Переименуйте ветку в main (если нужно)
git branch -M main

# Отправьте код на GitHub
git push -u origin main
```

Если GitHub попросит авторизацию:
- Используйте **Personal Access Token** (не пароль)
- Создайте токен: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
- Выберите права: `repo` (полный доступ к репозиториям)

## Шаг 3: Проверьте на GitHub

Откройте ваш репозиторий на GitHub - там должен быть весь код!

## Шаг 4: На ноутбуке

```bash
# Клонируйте репозиторий
git clone https://github.com/YOUR_USERNAME/secure-content-service.git

# Перейдите в папку
cd secure-content-service

# Запустите проект
docker-compose up -d
```

## Альтернатива: Через SSH (если настроен SSH ключ)

```bash
git remote add origin git@github.com:YOUR_USERNAME/secure-content-service.git
git push -u origin main
```

## Полезные команды

```bash
# Проверить подключенные репозитории
git remote -v

# Отправить изменения
git push

# Получить изменения
git pull

# Посмотреть статус
git status
```
