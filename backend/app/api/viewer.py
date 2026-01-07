"""
API для просмотра документов
"""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from fastapi.templating import Jinja2Templates
from pathlib import Path
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.models.database import get_db, Document, User, ViewingSession, DocumentAccess
from app.models.schemas import ViewerTokenResponse
from app.core.config import settings

router = APIRouter()

def get_client_ip(request: Request) -> str:
    """Получает реальный IP адрес клиента из заголовков"""
    ip_headers = [
        "X-Forwarded-For",
        "X-Real-IP",
        "X-Client-IP",
        "CF-Connecting-IP",
        "True-Client-IP",
        "X-Forwarded",
        "Forwarded-For",
        "Forwarded"
    ]
    
    print(f"[GET_CLIENT_IP] Checking headers for IP address...")
    print(f"[GET_CLIENT_IP] request.client.host: {request.client.host if request.client else 'None'}")
    
    # Проверяем заголовки
    for header in ip_headers:
        ip_value = request.headers.get(header)
        if ip_value:
            print(f"[GET_CLIENT_IP] Found header {header}: {ip_value}")
            ip = ip_value.split(",")[0].strip()
            if ip and ip not in ["127.0.0.1", "localhost", "::1"]:
                # Пропускаем Docker internal IPs и локальные сети
                if not (ip.startswith("172.17.") or ip.startswith("172.18.") or 
                       ip.startswith("172.19.") or ip.startswith("172.20.") or
                       ip.startswith("10.") or ip.startswith("192.168.")):
                    print(f"[GET_CLIENT_IP] Returning IP from header {header}: {ip}")
                    return ip
    
    if request.client:
        client_host = request.client.host
        print(f"[GET_CLIENT_IP] Client host: {client_host}")
        
        # Если это Docker internal IP или локальная сеть
        if (client_host.startswith("172.17.") or client_host.startswith("172.18.") or 
            client_host.startswith("172.19.") or client_host.startswith("172.20.") or
            client_host.startswith("10.") or client_host.startswith("192.168.")):
            print(f"[GET_CLIENT_IP] Client host is Docker/internal IP: {client_host}")
            # Пробуем получить из X-Forwarded-For даже если это Docker IP
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
                print(f"[GET_CLIENT_IP] X-Forwarded-For found: {ip}")
                if ip and not (ip.startswith("172.") or ip.startswith("10.") or ip.startswith("192.168.")):
                    return ip
            
            # Пробуем получить из referer (может содержать информацию о клиенте)
            referer = request.headers.get("referer")
            if referer:
                print(f"[GET_CLIENT_IP] Referer: {referer}")
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(referer)
                    # Если referer указывает на внешний сайт, можем использовать его домен как индикатор
                    # Но это не даст нам реальный IP
                    pass
                except:
                    pass
            
            # Если запрос идет напрямую без прокси, используем host из URL запроса
            # Это может быть внешний IP сервера, но не IP клиента
            host = request.headers.get("host")
            if host and ":" in host:
                host_ip = host.split(":")[0]
                # Проверяем, что это не localhost
                if host_ip not in ["localhost", "127.0.0.1"] and not host_ip.startswith("172."):
                    print(f"[GET_CLIENT_IP] Using host IP: {host_ip}")
                    # Но это IP сервера, а не клиента, поэтому не подходит
            
            print(f"[GET_CLIENT_IP] No valid IP found, returning 'unknown'")
            return "unknown"
        
        print(f"[GET_CLIENT_IP] Returning client_host: {client_host}")
        return client_host
    
    print(f"[GET_CLIENT_IP] No client info, returning 'unknown'")
    return "unknown"

# Templates для viewer
# Ищем templates в нескольких возможных местах
import os
import sys

# Определяем базовый путь приложения
BASE_DIR = Path("/app")
if not BASE_DIR.exists():
    # Если не в Docker, используем относительный путь
    BASE_DIR = Path(__file__).parent.parent.parent.parent

possible_templates_dirs = [
    Path("/app/frontend/templates"),  # Абсолютный путь в Docker контейнере
    BASE_DIR / "frontend" / "templates",
    Path(__file__).parent.parent.parent.parent / "frontend" / "templates",
    Path("frontend/templates"),
    Path("../frontend/templates"),
]

templates_dir = None
for td in possible_templates_dirs:
    try:
        if td.exists() and td.is_dir():
            # Проверяем наличие viewer.html
            viewer_file = td / "viewer.html"
            if viewer_file.exists():
                templates_dir = td.resolve() if not td.is_absolute() else td
                break
    except Exception as e:
        continue

def get_templates():
    """Получить объект templates, переинициализируя при необходимости"""
    global templates_dir
    if templates_dir:
        try:
            return Jinja2Templates(directory=str(templates_dir))
        except Exception as e:
            print(f"Error creating Jinja2Templates: {e}")
            return None
    return None

# Инициализируем templates при импорте модуля
templates = get_templates()
if templates:
    print(f"Templates initialized from: {templates_dir}")
else:
    print("WARNING: Templates not initialized!")


def check_referer(request: Request) -> bool:
    """Проверка Referer и Origin для защиты от прямого доступа"""
    if not settings.REQUIRE_REFERER_CHECK:
        return True
    
    if not settings.ALLOWED_EMBED_DOMAINS:
        return True  # Если домены не указаны, разрешаем доступ
    
    # Проверяем и Referer, и Origin (браузеры могут отправлять разные заголовки)
    referer = request.headers.get("referer")
    origin = request.headers.get("origin")
    
    # Если оба заголовка отсутствуют, проверяем Host заголовок (для прямого доступа)
    if not referer and not origin:
        # Логируем для отладки
        print(f"[REFERER CHECK] No Referer or Origin header. Headers: {dict(request.headers)}")
        return False
    
    def check_domain(header_value: str) -> bool:
        """Проверка домена из заголовка"""
        if not header_value:
            return False
        
        try:
            # Если это Origin, он уже содержит только домен (без пути)
            if header_value.startswith('http://') or header_value.startswith('https://'):
                parsed = urlparse(header_value)
                header_domain = parsed.netloc.lower()
            else:
                # Origin может быть просто доменом
                header_domain = header_value.lower()
            
            # Проверяем каждый разрешенный домен
            for allowed_domain in settings.ALLOWED_EMBED_DOMAINS:
                allowed_parsed = urlparse(allowed_domain if allowed_domain.startswith('http') else f'https://{allowed_domain}')
                allowed_domain_clean = allowed_parsed.netloc.lower().replace('www.', '')
                header_domain_clean = header_domain.replace('www.', '')
                
                if header_domain_clean == allowed_domain_clean:
                    print(f"[REFERER CHECK] Match found: {header_domain_clean} == {allowed_domain_clean}")
                    return True
            
            return False
        except Exception as e:
            print(f"[REFERER CHECK] Error parsing domain: {e}")
            return False
    
    # Проверяем Referer
    if referer:
        if check_domain(referer):
            return True
    
    # Проверяем Origin (более надежен для iframe)
    if origin:
        if check_domain(origin):
            return True
    
    print(f"[REFERER CHECK] No match. Referer: {referer}, Origin: {origin}")
    return False


class ViewerTokenRequest(BaseModel):
    document_token: str
    user_email: Optional[str] = None  # Опционально - для водяных знаков из Tilda


@router.post("/token", response_model=ViewerTokenResponse)
async def create_viewer_token(
    request: Request,
    data: ViewerTokenRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Создание токена для просмотра документа (упрощенная версия - только проверка referer)"""
    # Проверка Referer (основная защита) - только если REQUIRE_REFERER_CHECK=true
    if settings.REQUIRE_REFERER_CHECK and not check_referer(request):
        raise HTTPException(
            status_code=403, 
            detail="Доступ разрешен только с разрешенных доменов"
        )
    
    # Находим документ
    doc = db.query(Document).filter(Document.access_token == data.document_token).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    # Если передан user_email, находим или создаем пользователя для водяных знаков
    user_id = None
    if data.user_email:
        from app.models.database import User
        user = db.query(User).filter(User.email == data.user_email).first()
        if not user:
            # Создаем пользователя автоматически для водяных знаков
            user = User(email=data.user_email, name=data.user_email.split('@')[0])
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    
    # Очищаем старые сессии (старше 7 дней) перед созданием новой
    # Это предотвращает переполнение базы данных
    try:
        old_date = datetime.utcnow() - timedelta(days=7)
        deleted_count = db.query(ViewingSession).filter(
            ViewingSession.created_at < old_date
        ).delete()
        if deleted_count > 0:
            db.commit()
            print(f"[CLEANUP] Deleted {deleted_count} old viewing sessions")
    except Exception as e:
        print(f"[WARN] Failed to cleanup old sessions: {e}")
        db.rollback()
    
    # Создаем сессию просмотра
    viewer_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    # Получаем реальный IP адрес клиента
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    
    # Создаем сессию (user_id может быть NULL)
    session = ViewingSession(
        document_id=doc.id,
        user_id=user_id,  # Может быть None или ID пользователя из Tilda
        session_token=viewer_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    
    return ViewerTokenResponse(
        viewer_token=viewer_token,
        viewer_url=f"/viewer?token={viewer_token}",
        expires_at=expires_at
    )


@router.get("/", response_class=HTMLResponse)
async def viewer_page(token: str, request: Request, db: Session = Depends(get_db)):
    """Страница просмотра документа"""
    # Проверяем сессию ПЕРВЫМ делом (до проверки referer)
    session = db.query(ViewingSession).filter(ViewingSession.session_token == token).first()
    if not session:
        raise HTTPException(status_code=403, detail="Сессия недействительна")
    
    if datetime.utcnow() > session.expires_at:
        raise HTTPException(status_code=403, detail="Сессия истекла")
    
    # Проверка Referer (защита от прямого доступа)
    # ВАЖНО: Для локального тестирования проверка отключена если REQUIRE_REFERER_CHECK=false
    if settings.REQUIRE_REFERER_CHECK:
        referer = request.headers.get("referer")
        # Если Referer указывает на сам сервер (внутренний запрос из iframe, созданного через /embed),
        # разрешаем доступ - это нормальное поведение для встроенного viewer
        allow_access = False
        if referer:
            try:
                referer_parsed = urlparse(referer)
                referer_host = referer_parsed.netloc.lower().split(':')[0]  # Убираем порт для сравнения
                request_host = request.url.hostname.lower() if request.url.hostname else ""
                # Если Referer указывает на тот же сервер, разрешаем (внутренний запрос из iframe)
                if referer_host == request_host:
                    print(f"[VIEWER] Allowing internal request from same server: {referer_host} == {request_host}")
                    allow_access = True
            except Exception as e:
                print(f"[VIEWER] Error checking referer: {e}")
        
        # Если это не внутренний запрос, проверяем через стандартную функцию
        if not allow_access:
            if check_referer(request):
                allow_access = True
        
        if not allow_access:
            raise HTTPException(
                status_code=403, 
                detail="Доступ разрешен только с разрешенных доменов"
            )
    
    # Обновляем время последнего доступа
    session.last_access = datetime.utcnow()
    db.commit()
    
    # Получаем документ
    doc = session.document
    user = session.user  # Может быть None в упрощенной версии
    
    # Получаем глобальные настройки водяных знаков для передачи в шаблон
    from app.models.database import GlobalWatermarkSettings
    import json
    from app.models.schemas import WatermarkSettings
    
    watermark_settings = WatermarkSettings().dict()
    global_settings = db.query(GlobalWatermarkSettings).first()
    if global_settings and global_settings.settings_json:
        try:
            settings_dict = json.loads(global_settings.settings_json)
            watermark_settings = settings_dict
        except:
            pass
    
    context = {
        "request": request,
        "token": token,
        "document_id": doc.id,
        "document_name": doc.name,
        "total_pages": doc.total_pages,
        "user_email": user.email if user else None,
        "user_id": str(session.user_id) if session.user_id else None,
        "ip_address": session.ip_address or "127.0.0.1",
        "watermark_settings": watermark_settings
    }
    
    # Переинициализируем templates на случай hot-reload
    current_templates = get_templates()
    if current_templates:
        try:
            return current_templates.TemplateResponse("viewer.html", context)
        except Exception as e:
            import traceback
            error_msg = f"Template rendering error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            # Fallback на простой HTML - продолжаем выполнение
            pass
    
    # Fallback: возвращаем простой HTML
    if not current_templates:
        # Fallback: возвращаем простой HTML
        from fastapi.responses import HTMLResponse
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{doc.name}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <h1>Viewer для {doc.name}</h1>
            <p>Токен: {token}</p>
            <p>Страниц: {doc.total_pages}</p>
            <p>Пользователь: {user.email}</p>
            <p>Для полноценного viewer используйте шаблон из frontend/templates/viewer.html</p>
        </body>
        </html>
        """)


@router.get("/info")
async def get_viewer_info(token: str, request: Request, db: Session = Depends(get_db)):
    """Получение информации о документе для viewer"""
    print(f"[VIEWER INFO] Request received. Token: {token[:20]}...")
    print(f"[VIEWER INFO] Referer: {request.headers.get('referer', 'None')}")
    print(f"[VIEWER INFO] Origin: {request.headers.get('origin', 'None')}")
    # Проверка Referer
    if settings.REQUIRE_REFERER_CHECK:
        referer = request.headers.get("referer")
        # Если Referer указывает на сам сервер (внутренний запрос из iframe), разрешаем доступ
        allow_access = False
        if referer:
            try:
                referer_parsed = urlparse(referer)
                referer_host = referer_parsed.netloc.lower().split(':')[0]  # Убираем порт для сравнения
                request_host = request.url.hostname.lower() if request.url.hostname else ""
                if referer_host == request_host:
                    print(f"[VIEWER INFO] Allowing internal request from same server: {referer_host}")
                    allow_access = True
            except Exception as e:
                print(f"[VIEWER INFO] Error checking referer: {e}")
        
        if not allow_access and check_referer(request):
            allow_access = True
        
        if not allow_access:
            raise HTTPException(
                status_code=403, 
                detail="Доступ разрешен только с разрешенных доменов"
            )
    
    session = db.query(ViewingSession).filter(ViewingSession.session_token == token).first()
    if not session:
        raise HTTPException(status_code=403, detail="Сессия недействительна")
    
    if datetime.utcnow() > session.expires_at:
        raise HTTPException(status_code=403, detail="Сессия истекла")
    
    doc = session.document
    user = session.user  # Может быть None
    
    # Получаем глобальные настройки водяных знаков
    from app.models.database import GlobalWatermarkSettings
    import json
    from app.models.schemas import WatermarkSettings
    
    watermark_settings = WatermarkSettings().dict()
    global_settings = db.query(GlobalWatermarkSettings).first()
    if global_settings and global_settings.settings_json:
        try:
            settings_dict = json.loads(global_settings.settings_json)
            watermark_settings = settings_dict
        except:
            pass
    
    result = {
        "document_id": doc.id,
        "document_name": doc.name,
        "total_pages": doc.total_pages,
        "user_email": user.email if user else None,
        "user_id": str(session.user_id) if session.user_id else None,
        "ip_address": session.ip_address or "127.0.0.1",
        "expires_at": session.expires_at.isoformat(),
        "watermark_settings": watermark_settings
    }
    print(f"[VIEWER INFO] Returning data. Document ID: {doc.id}, Total pages: {doc.total_pages}")
    return result


@router.get("/embed")
async def embed_viewer(
    document_token: str,
    request: Request,
    user_email: Optional[str] = None,  # Опционально - для водяных знаков из Tilda
    source_domain: Optional[str] = None,  # Временный параметр для отладки (менее безопасно)
    client_ip: Optional[str] = None,  # IP адрес клиента, полученный через JavaScript
    db: Session = Depends(get_db)
):
    """
    Embed endpoint для встраивания viewer в Tilda и другие сайты
    Автоматически создает сессию и возвращает HTML для iframe
    Упрощенная версия - только проверка referer
    """
    # Логирование для отладки
    referer = request.headers.get("referer", "None")
    origin = request.headers.get("origin", "None")
    print(f"[EMBED] Request from Referer: {referer}")
    print(f"[EMBED] Request from Origin: {origin}")
    print(f"[EMBED] Document token: {document_token}")
    print(f"[EMBED] User email: {user_email}")
    print(f"[EMBED] Source domain parameter (from function): {source_domain}")
    print(f"[EMBED] Client IP parameter (from function): {client_ip}")
    print(f"[EMBED] Full URL: {request.url}")
    print(f"[EMBED] Query params: {dict(request.query_params)}")
    
    # Если client_ip не передан в функцию, пробуем получить из query
    if not client_ip:
        client_ip = request.query_params.get("client_ip")
        print(f"[EMBED] Client IP from query params: {client_ip}")
    # Проверяем параметр напрямую из query
    source_domain_from_query = request.query_params.get("source_domain")
    print(f"[EMBED] Source domain from query params: {source_domain_from_query}")
    print(f"[EMBED] REQUIRE_REFERER_CHECK: {settings.REQUIRE_REFERER_CHECK}")
    print(f"[EMBED] ALLOWED_EMBED_DOMAINS: {settings.ALLOWED_EMBED_DOMAINS}")
    print(f"[EMBED] All headers: {dict(request.headers)}")
    
    # Используем параметр из query, если он не передан в функцию
    if not source_domain and source_domain_from_query:
        source_domain = source_domain_from_query
        print(f"[EMBED] Using source_domain from query params: {source_domain}")
    
    # Проверка Referer для embed (основная защита) - только если REQUIRE_REFERER_CHECK=true
    if settings.REQUIRE_REFERER_CHECK:
        referer_check_result = check_referer(request)
        print(f"[EMBED] Referer check result: {referer_check_result}")
        
        # Временная проверка через параметр source_domain (для отладки, менее безопасно)
        if not referer_check_result:
            if source_domain:
                print(f"[EMBED] Trying source_domain parameter check: {source_domain}")
                try:
                    source_parsed = urlparse(source_domain if source_domain.startswith('http') else f'https://{source_domain}')
                    source_domain_clean = source_parsed.netloc.lower().replace('www.', '')
                    print(f"[EMBED] Parsed source_domain_clean: {source_domain_clean}")
                    for allowed_domain in settings.ALLOWED_EMBED_DOMAINS:
                        allowed_parsed = urlparse(allowed_domain if allowed_domain.startswith('http') else f'https://{allowed_domain}')
                        allowed_domain_clean = allowed_parsed.netloc.lower().replace('www.', '')
                        print(f"[EMBED] Comparing: '{source_domain_clean}' == '{allowed_domain_clean}'")
                        if source_domain_clean == allowed_domain_clean:
                            print(f"[EMBED] Source domain match: {source_domain_clean}")
                            referer_check_result = True
                            break
                except Exception as e:
                    print(f"[EMBED] Error checking source_domain: {e}")
                    import traceback
                    print(f"[EMBED] Traceback: {traceback.format_exc()}")
            else:
                print(f"[EMBED] source_domain parameter is None or empty")
                # ВРЕМЕННО: Если параметр не передан, но есть заголовок sec-fetch-site: cross-site,
                # и это запрос для iframe, разрешаем доступ (только для отладки!)
                # ВНИМАНИЕ: Это небезопасно для продакшена!
                sec_fetch_site = request.headers.get("sec-fetch-site", "")
                sec_fetch_dest = request.headers.get("sec-fetch-dest", "")
                print(f"[EMBED] sec-fetch-site: {sec_fetch_site}, sec-fetch-dest: {sec_fetch_dest}")
                if sec_fetch_site == "cross-site" and sec_fetch_dest == "iframe":
                    print(f"[EMBED] WARNING: Temporarily allowing access for cross-site iframe (DEBUG MODE)")
                    print(f"[EMBED] This is INSECURE and should be removed in production!")
                    referer_check_result = True
        
        if not referer_check_result:
            print(f"[EMBED] Access denied - referer not allowed")
            raise HTTPException(
                status_code=403, 
                detail="Встраивание разрешено только с разрешенных доменов"
            )
    
    # Находим документ
    doc = db.query(Document).filter(Document.access_token == document_token).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    # Если передан user_email, находим или создаем пользователя для водяных знаков
    user_id = None
    if user_email:
        from app.models.database import User
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            # Создаем пользователя автоматически для водяных знаков
            user = User(email=user_email, name=user_email.split('@')[0])
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
    
    # Создаем сессию
    viewer_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    # Получаем реальный IP адрес клиента
    # Сначала пробуем использовать IP, переданный из JavaScript (если есть)
    if client_ip and client_ip != "unknown" and not client_ip.startswith("172.") and not client_ip.startswith("10.") and not client_ip.startswith("192.168."):
        ip_address = client_ip
        print(f"[EMBED] Using client IP from parameter: {ip_address}")
    else:
        ip_address = get_client_ip(request) if request else "unknown"
        print(f"[EMBED] Using IP from get_client_ip: {ip_address}")
    
    user_agent = request.headers.get("user-agent") if request else None
    
    session = ViewingSession(
        document_id=doc.id,
        user_id=user_id,  # Может быть None или ID пользователя из Tilda
        session_token=viewer_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    
    # Возвращаем HTML с iframe
    viewer_url = f"/viewer?token={viewer_token}"
    
    # Получаем host
    host = request.headers.get("Host", request.url.hostname) or "lessons.incrypto.ru"
    host_str = str(host).lower().strip()
    
    # КРИТИЧЕСКИ ВАЖНО: ВСЕГДА используем HTTPS для production домена
    # Это необходимо для работы через HTTPS сайты (Tilda) и предотвращения Mixed Content ошибок
    # Убираем порт из host если есть (например, lessons.incrypto.ru:8000 -> lessons.incrypto.ru)
    if ':' in host_str:
        host_str = host_str.split(':')[0]
        host = host.split(':')[0]
    
    # ПРИНУДИТЕЛЬНО используем HTTPS для lessons.incrypto.ru
    # Не зависим от request.url.scheme, так как он может быть HTTP из-за прокси
    if "lessons.incrypto.ru" in host_str or host_str == "lessons.incrypto.ru":
        base_url = "https://lessons.incrypto.ru"
        print(f"[EMBED] FORCED HTTPS for lessons.incrypto.ru domain: {base_url}")
    else:
        # Для других доменов всегда используем HTTPS по умолчанию
        base_url = f"https://{host}".rstrip('/')
        print(f"[EMBED] Using HTTPS for domain: {host} -> {base_url}")
    
    # Дополнительная проверка: убеждаемся, что base_url всегда HTTPS
    if base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://")
        print(f"[EMBED] WARNING: Fixed HTTP to HTTPS: {base_url}")
    
    scheme = "https"  # Всегда HTTPS
    
    # Логирование для отладки
    referer = request.headers.get("Referer", "")
    origin = request.headers.get("Origin", "")
    x_forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
    print(f"[EMBED] Host: {host}, Host (str): {host_str}")
    print(f"[EMBED] Referer: {referer}")
    print(f"[EMBED] Origin: {origin}")
    print(f"[EMBED] X-Forwarded-Proto: {x_forwarded_proto}")
    print(f"[EMBED] Request URL scheme: {request.url.scheme}")
    print(f"[EMBED] Final scheme: {scheme}")
    # Финальная проверка и исправление URL
    final_viewer_url = f"{base_url}{viewer_url}"
    if final_viewer_url.startswith("http://"):
        final_viewer_url = final_viewer_url.replace("http://", "https://")
        print(f"[EMBED] WARNING: Final URL was HTTP, fixed to: {final_viewer_url}")
    
    print(f"[EMBED] Final base_url: {base_url}")
    print(f"[EMBED] Final viewer URL: {final_viewer_url}")
    
    # Создаем ответ с заголовками для принудительного использования HTTPS
    response = HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
        <title>{doc.name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: transparent;
                margin: 0;
                padding: 0;
            }}
            html, body {{
                width: 100%;
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }}
            .embed-container {{
                width: 100%;
                height: 100%;
                border: none;
                margin: 0;
                padding: 0;
                display: block;
            }}
            .loading {{
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-size: 18px;
                color: #666;
                background: transparent;
            }}
        </style>
    </head>
    <body>
        <div id="loading" class="loading">Загрузка документа...</div>
        <iframe 
            id="viewerFrame"
            class="embed-container"
            src="{final_viewer_url}"
            frameborder="0"
            allowfullscreen
            style="display: none; width: 100%; height: 100%; border: none; margin: 0; padding: 0;"
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
            loading="eager"
        ></iframe>
        <script>
            // КРИТИЧЕСКИ ВАЖНО: Принудительное исправление URL на HTTPS
            (function() {{
                const iframe = document.getElementById('viewerFrame');
                if (!iframe) {{
                    console.error('[EMBED] Iframe not found!');
                    return;
                }}
                
                // ПРИНУДИТЕЛЬНО устанавливаем HTTPS URL
                const viewerUrl = '{final_viewer_url}';
                let httpsUrl = viewerUrl;
                
                // Если URL начинается с http://, заменяем на https://
                if (httpsUrl.startsWith('http://')) {{
                    httpsUrl = httpsUrl.replace('http://', 'https://');
                    console.log('[EMBED] FIXING HTTP to HTTPS:', viewerUrl, '->', httpsUrl);
                }}
                
                // Если URL относительный, делаем абсолютный с HTTPS
                if (!httpsUrl.startsWith('http')) {{
                    httpsUrl = 'https://lessons.incrypto.ru' + (httpsUrl.startsWith('/') ? httpsUrl : '/' + httpsUrl);
                    console.log('[EMBED] Converting relative to HTTPS:', viewerUrl, '->', httpsUrl);
                }}
                
                // Устанавливаем URL
                console.log('[EMBED] Setting iframe src to:', httpsUrl);
                iframe.src = httpsUrl;
                iframe.setAttribute('src', httpsUrl);
                
                // Дополнительная проверка через небольшую задержку
                setTimeout(function() {{
                    const currentSrc = iframe.src || iframe.getAttribute('src');
                    if (currentSrc && currentSrc.startsWith('http://')) {{
                        console.error('[EMBED] ERROR: Iframe src changed to HTTP:', currentSrc);
                        const fixedSrc = currentSrc.replace('http://', 'https://');
                        console.log('[EMBED] Fixing again to:', fixedSrc);
                        iframe.src = fixedSrc;
                        iframe.setAttribute('src', fixedSrc);
                    }}
                }}, 100);
                
                // Проверка после загрузки
                iframe.addEventListener('load', function() {{
                    const finalSrc = iframe.src || iframe.getAttribute('src');
                    console.log('[EMBED] Iframe loaded, final src:', finalSrc);
                    if (finalSrc && finalSrc.startsWith('http://')) {{
                        console.error('[EMBED] ERROR: Iframe still using HTTP after load:', finalSrc);
                        const httpsSrc = finalSrc.replace('http://', 'https://');
                        iframe.src = httpsSrc;
                        iframe.setAttribute('src', httpsSrc);
                    }}
                }});
            }})();
        </script>
        <script>
            const iframe = document.getElementById('viewerFrame');
            const loading = document.getElementById('loading');
            
            iframe.onload = function() {{
                loading.style.display = 'none';
                iframe.style.display = 'block';
            }};
            
            iframe.onerror = function() {{
                loading.textContent = 'Ошибка загрузки документа';
            }};
        </script>
    </body>
    </html>
    """)
    
    # Добавляем заголовки для принудительного использования HTTPS
    response.headers["Content-Security-Policy"] = "upgrade-insecure-requests"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response
    
    # Добавляем заголовки для принудительного использования HTTPS
    response.headers["Content-Security-Policy"] = "upgrade-insecure-requests"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response