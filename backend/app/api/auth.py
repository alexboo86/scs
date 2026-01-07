"""
API для аутентификации администраторов
"""
from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.database import get_db, AdminUser
from app.core.security import verify_password, create_access_token, decode_access_token
from datetime import timedelta
from app.core.config import settings
from pathlib import Path

router = APIRouter()

# Templates для страницы входа
possible_templates_dirs = [
    Path("/app/frontend/templates"),
    Path(__file__).parent.parent.parent.parent / "frontend" / "templates",
    Path(__file__).parent.parent.parent.parent.parent / "frontend" / "templates",
    Path("frontend/templates"),
    Path("../frontend/templates"),
]

templates_dir = None
for td in possible_templates_dirs:
    if td.exists():
        templates_dir = td
        break

if templates_dir:
    templates = Jinja2Templates(directory=str(templates_dir))
else:
    templates = None


def get_current_admin(
    token: str = None,
    db: Session = Depends(get_db)
) -> AdminUser:
    """Получение текущего администратора из токена"""
    if not token:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Недействительный токен")
    
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Администратор не найден или неактивен")
    
    return admin


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    if templates:
        return templates.TemplateResponse("admin_login.html", {"request": request})
    else:
        return HTMLResponse("""
        <html>
        <head><title>Admin Login</title></head>
        <body>
            <h1>Admin Login</h1>
            <p>Шаблон admin_login.html не найден.</p>
        </body>
        </html>
        """)


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Авторизация администратора"""
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    
    if not verify_password(password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    
    # Создаем токен
    access_token = create_access_token(
        data={"sub": admin.username},
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    
    # Проверяем, является ли запрос AJAX (через заголовок)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or \
              request.headers.get("Content-Type", "").startswith("application/json")
    
    if is_ajax:
        # Для AJAX запросов возвращаем JSON
        from fastapi.responses import JSONResponse
        response = JSONResponse({
            "status": "success",
            "token": access_token,
            "redirect": "/api/admin/"
        })
    else:
        # Для обычных форм возвращаем HTML с редиректом
        response = HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Авторизация...</title>
            <script>
                // Сохраняем токен в localStorage
                localStorage.setItem('admin_token', '{access_token}');
                // Немедленный редирект
                window.location.replace('/api/admin/');
            </script>
        </head>
        <body>
            <p>Авторизация успешна. Перенаправление...</p>
            <script>
                // Дополнительная проверка на случай, если первый редирект не сработал
                setTimeout(function() {{
                    window.location.href = '/api/admin/';
                }}, 100);
            </script>
        </body>
        </html>
        """)
    
    # Устанавливаем cookie для дополнительной безопасности
    response.set_cookie(
        key="admin_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        samesite="lax"
    )
    
    return response


@router.post("/logout")
async def logout():
    """Выход из системы"""
    response = HTMLResponse("""
    <html>
    <head>
        <title>Выход...</title>
        <script>
            localStorage.removeItem('admin_token');
            window.location.href = '/api/auth/login';
        </script>
    </head>
    <body>
        <p>Выход выполнен. Перенаправление...</p>
    </body>
    </html>
    """)
    response.delete_cookie(key="admin_token")
    return response
