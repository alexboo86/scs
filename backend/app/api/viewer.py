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

def is_mobile_device(user_agent: Optional[str]) -> bool:
    """Определяет, является ли устройство мобильным"""
    if not user_agent:
        return False
    
    user_agent_lower = user_agent.lower()
    mobile_keywords = [
        'iphone', 'ipad', 'ipod', 'android', 'mobile', 
        'blackberry', 'windows phone', 'opera mini', 'palm'
    ]
    
    return any(keyword in user_agent_lower for keyword in mobile_keywords)


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
    
    # Определяем, является ли устройство мобильным
    user_agent = request.headers.get("user-agent", "")
    is_mobile = is_mobile_device(user_agent)
    
    # Формируем base_url для API запросов (всегда HTTPS, особенно для мобильных)
    host = request.headers.get("Host", request.url.hostname) or "lessons.incrypto.ru"
    host_str = str(host).lower().strip()
    
    # Убираем порт из host если есть
    if ':' in host_str:
        host_str = host_str.split(':')[0]
        host = host.split(':')[0]
    
    # ВСЕГДА используем HTTPS, особенно для мобильных устройств
    if "lessons.incrypto.ru" in host_str or host_str == "lessons.incrypto.ru":
        api_base_url = "https://lessons.incrypto.ru"
    else:
        api_base_url = f"https://{host}".rstrip('/')
    
    if is_mobile:
        print(f"[VIEWER] Mobile device detected, forcing HTTPS API base: {api_base_url}")
    
    context = {
        "request": request,
        "token": token,
        "document_id": doc.id,
        "document_name": doc.name,
        "total_pages": doc.total_pages,
        "user_email": user.email if user else None,
        "user_id": str(session.user_id) if session.user_id else None,
        "ip_address": session.ip_address or "127.0.0.1",
        "watermark_settings": watermark_settings,
        "api_base_url": api_base_url,  # Передаем абсолютный HTTPS URL
        "is_mobile": is_mobile  # Флаг для мобильных устройств
    }
    
    # Переинициализируем templates на случай hot-reload
    current_templates = get_templates()
    if current_templates:
        try:
            response = current_templates.TemplateResponse("viewer.html", context)
            # КРИТИЧЕСКИ ВАЖНО: Принудительно устанавливаем HTTPS заголовки для мобильных устройств
            # Это предотвращает mixed content ошибки в Safari на iOS
            response.headers["Content-Security-Policy"] = "upgrade-insecure-requests; default-src https:"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            # Принудительно указываем, что это HTTPS соединение
            if is_mobile:
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "SAMEORIGIN"
                print(f"[VIEWER] Mobile device detected, added HTTPS security headers")
            return response
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
    
    # Определяем, является ли устройство мобильным
    user_agent = request.headers.get("user-agent", "")
    is_mobile = is_mobile_device(user_agent)
    
    if is_mobile:
        print(f"[EMBED] Mobile device detected: {user_agent[:100]}")
    
    # КРИТИЧЕСКИ ВАЖНО: ВСЕГДА используем HTTPS для production домена
    # Это необходимо для работы через HTTPS сайты (Tilda) и предотвращения Mixed Content ошибок
    # Особенно важно для мобильных устройств (iOS Safari строго блокирует mixed content)
    # Убираем порт из host если есть (например, lessons.incrypto.ru:8000 -> lessons.incrypto.ru)
    if ':' in host_str:
        host_str = host_str.split(':')[0]
        host = host.split(':')[0]
    
    # ПРИНУДИТЕЛЬНО используем HTTPS для lessons.incrypto.ru
    # Не зависим от request.url.scheme, так как он может быть HTTP из-за прокси
    # Для мобильных устройств ВСЕГДА используем HTTPS
    if "lessons.incrypto.ru" in host_str or host_str == "lessons.incrypto.ru":
        base_url = "https://lessons.incrypto.ru"
        if is_mobile:
            print(f"[EMBED] FORCED HTTPS for lessons.incrypto.ru domain (MOBILE): {base_url}")
        else:
            print(f"[EMBED] FORCED HTTPS for lessons.incrypto.ru domain: {base_url}")
    else:
        # Для других доменов всегда используем HTTPS по умолчанию
        # Для мобильных устройств принудительно HTTPS
        base_url = f"https://{host}".rstrip('/')
        if is_mobile:
            print(f"[EMBED] Using HTTPS for domain (MOBILE): {host} -> {base_url}")
        else:
            print(f"[EMBED] Using HTTPS for domain: {host} -> {base_url}")
    
    # Дополнительная проверка: убеждаемся, что base_url всегда HTTPS
    # Особенно важно для мобильных устройств
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
    
    # КРИТИЧЕСКИ ВАЖНО: Принудительно исправляем HTTP на HTTPS
    # Это особенно важно для мобильных устройств (iOS Safari)
    if final_viewer_url.startswith("http://"):
        final_viewer_url = final_viewer_url.replace("http://", "https://")
        print(f"[EMBED] WARNING: Final URL was HTTP, fixed to: {final_viewer_url}")
    
    # Дополнительная проверка: убеждаемся, что URL всегда HTTPS
    if not final_viewer_url.startswith("https://"):
        # Если URL не начинается с https://, добавляем его
        if final_viewer_url.startswith("//"):
            final_viewer_url = "https:" + final_viewer_url
        elif final_viewer_url.startswith("/"):
            final_viewer_url = base_url + final_viewer_url
        else:
            final_viewer_url = "https://" + final_viewer_url
        print(f"[EMBED] WARNING: URL didn't start with https://, fixed to: {final_viewer_url}")
    
    # Убираем возможный двойной слэш после домена
    final_viewer_url = final_viewer_url.replace("https://lessons.incrypto.ru//", "https://lessons.incrypto.ru/")
    
    print(f"[EMBED] Final base_url: {base_url}")
    print(f"[EMBED] Final viewer URL: {final_viewer_url}")
    print(f"[EMBED] Is mobile: {is_mobile}")
    print(f"[EMBED] User-Agent: {user_agent[:100] if user_agent else 'None'}")
    
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
            allow="fullscreen"
            webkitallowfullscreen
            mozallowfullscreen
            msallowfullscreen
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
                // Используем base_url из сервера вместо хардкода
                if (!httpsUrl.startsWith('http')) {{
                    const baseUrl = '{base_url}';
                    httpsUrl = baseUrl + (httpsUrl.startsWith('/') ? httpsUrl : '/' + httpsUrl);
                    console.log('[EMBED] Converting relative to HTTPS:', viewerUrl, '->', httpsUrl);
                }}
                
                // Дополнительная проверка для мобильных устройств
                const isMobile = /iPhone|iPad|iPod|Android|Mobile|BlackBerry|Windows Phone|Opera Mini|Palm/i.test(navigator.userAgent);
                if (isMobile) {{
                    // Для мобильных устройств принудительно используем HTTPS
                    if (httpsUrl.startsWith('http://')) {{
                        httpsUrl = httpsUrl.replace('http://', 'https://');
                        console.log('[EMBED] MOBILE: Forced HTTPS conversion:', httpsUrl);
                    }}
                    // Убираем возможный двойной слэш
                    httpsUrl = httpsUrl.replace(/(https?:\/\/[^\/]+)\/\//, '$1/');
                }}
                
                // КРИТИЧЕСКИ ВАЖНО: Финальная проверка - убеждаемся, что URL всегда HTTPS
                if (!httpsUrl.startsWith('https://')) {{
                    if (httpsUrl.startsWith('//')) {{
                        httpsUrl = 'https:' + httpsUrl;
                    }} else if (httpsUrl.startsWith('/')) {{
                        httpsUrl = '{base_url}' + httpsUrl;
                    }} else {{
                        httpsUrl = 'https://' + httpsUrl;
                    }}
                    console.log('[EMBED] Final HTTPS fix:', httpsUrl);
                }}
                
                // Убираем возможный двойной слэш после домена
                httpsUrl = httpsUrl.replace(/(https:\/\/[^\/]+)\/\//, '$1/');
                
                // Устанавливаем URL
                console.log('[EMBED] Setting iframe src to:', httpsUrl);
                console.log('[EMBED] Is mobile device:', isMobile);
                iframe.src = httpsUrl;
                iframe.setAttribute('src', httpsUrl);
                
                // КРИТИЧЕСКИ ВАЖНО: Дополнительная проверка через MutationObserver для мобильных устройств
                if (isMobile) {{
                    const observer = new MutationObserver(function(mutations) {{
                        mutations.forEach(function(mutation) {{
                            if (mutation.type === 'attributes' && mutation.attributeName === 'src') {{
                                const currentSrc = iframe.src || iframe.getAttribute('src');
                                if (currentSrc && currentSrc.startsWith('http://')) {{
                                    console.error('[EMBED] MOBILE: Detected HTTP URL change, fixing:', currentSrc);
                                    const fixedSrc = currentSrc.replace('http://', 'https://');
                                    iframe.src = fixedSrc;
                                    iframe.setAttribute('src', fixedSrc);
                                }}
                            }}
                        }});
                    }});
                    observer.observe(iframe, {{ attributes: true, attributeFilter: ['src'] }});
                }}
                
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
            // Обработчик сообщений от viewer для полноэкранного режима
            window.addEventListener('message', function(event) {{
                // Проверяем источник сообщения (должен быть с нашего домена)
                const allowedOrigins = ['https://lessons.incrypto.ru', 'http://lessons.incrypto.ru'];
                const isAllowedOrigin = allowedOrigins.some(origin => event.origin.includes(origin.replace('https://', '').replace('http://', '')));
                
                if (!isAllowedOrigin) {{
                    console.log('[EMBED] Message from unauthorized origin:', event.origin);
                    return;
                }}
                
                console.log('[EMBED] Received message:', event.data, 'from:', event.origin);
                
                if (event.data && event.data.type === 'request-fullscreen') {{
                    const iframe = document.getElementById('viewerFrame');
                    if (!iframe) {{
                        console.error('[EMBED] Iframe not found');
                        return;
                    }}
                    
                    if (event.data.action === 'enter') {{
                        // Входим в полноэкранный режим
                        console.log('[EMBED] Entering fullscreen mode for iframe');
                        
                        // Получаем размеры экрана из сообщения или определяем сами
                        const requestedScreenWidth = event.data.screenWidth || window.screen.width || window.innerWidth;
                        const requestedScreenHeight = event.data.screenHeight || window.screen.height || window.innerHeight;
                        
                        // КРИТИЧЕСКИ ВАЖНО: Для мобильных устройств используем window.open для открытия viewer в новом окне
                        // Это самый надежный способ обойти ограничения контейнера Tilda на iOS
                        const isMobile = /iPhone|iPad|iPod|Android|Mobile|BlackBerry|Windows Phone|Opera Mini|Palm/i.test(navigator.userAgent);
                        
                        if (isMobile) {{
                            console.log('[EMBED] Mobile device detected, opening viewer in new window');
                            // Получаем URL viewer из iframe
                            const viewerUrl = iframe.src;
                            if (viewerUrl) {{
                                // Открываем viewer в новом окне на весь экран
                                const newWindow = window.open(
                                    viewerUrl,
                                    '_blank',
                                    'fullscreen=yes,location=no,menubar=no,scrollbars=yes,status=no,toolbar=no,width=' + requestedScreenWidth + ',height=' + requestedScreenHeight
                                );
                                
                                if (newWindow) {{
                                    console.log('[EMBED] Viewer opened in new window - NOT applying CSS changes to iframe');
                                    // Отправляем подтверждение viewer
                                    iframe.contentWindow.postMessage({{
                                        type: 'fullscreen-response',
                                        success: true,
                                        screenWidth: requestedScreenWidth,
                                        screenHeight: requestedScreenHeight,
                                        openedInNewWindow: true
                                    }}, '*');
                                    
                                    // Скрываем текущий iframe (но НЕ применяем CSS изменения)
                                    iframe.style.display = 'none';
                                    
                                    // Сохраняем ссылку на новое окно для закрытия при выходе
                                    window.fullscreenWindow = newWindow;
                                    
                                    // Слушаем закрытие нового окна
                                    const checkClosed = setInterval(() => {{
                                        if (newWindow.closed) {{
                                            clearInterval(checkClosed);
                                            console.log('[EMBED] New window closed, restoring iframe');
                                            
                                            // КРИТИЧЕСКИ ВАЖНО: Если iframe был перемещен в body, возвращаем его обратно
                                            if (window.originalIframeParent && iframe.parentElement === document.body) {{
                                                console.log('[EMBED] Restoring iframe to original parent');
                                                if (window.originalIframeNextSibling) {{
                                                    window.originalIframeParent.insertBefore(iframe, window.originalIframeNextSibling);
                                                }} else {{
                                                    window.originalIframeParent.appendChild(iframe);
                                                }}
                                                window.originalIframeParent = null;
                                                window.originalIframeNextSibling = null;
                                            }}
                                            
                                            // Восстанавливаем все стили iframe
                                            iframe.style.cssText = '';
                                            iframe.style.width = '100%';
                                            iframe.style.height = '100%';
                                            iframe.style.display = 'block';
                                            
                                            // Восстанавливаем стили body и html если они были изменены
                                            document.body.style.cssText = '';
                                            document.documentElement.style.cssText = '';
                                            
                                            // Восстанавливаем стили родительских элементов если они были изменены
                                            if (window.fullscreenParentStyles) {{
                                                let parent = iframe.parentElement;
                                                while (parent && parent !== document.body && parent !== document.documentElement) {{
                                                    if (window.fullscreenParentStyles.has(parent)) {{
                                                        const styles = window.fullscreenParentStyles.get(parent);
                                                        parent.style.position = styles.position || '';
                                                        parent.style.width = styles.width || '';
                                                        parent.style.height = styles.height || '';
                                                        parent.style.maxWidth = styles.maxWidth || '';
                                                        parent.style.maxHeight = styles.maxHeight || '';
                                                        parent.style.overflow = styles.overflow || '';
                                                        parent.style.margin = styles.margin || '';
                                                        parent.style.padding = styles.padding || '';
                                                        parent.style.zIndex = styles.zIndex || '';
                                                    }}
                                                    parent = parent.parentElement;
                                                }}
                                                window.fullscreenParentStyles.clear();
                                            }}
                                            
                                            // Отправляем сообщение о выходе из fullscreen
                                            iframe.contentWindow.postMessage({{
                                                type: 'fullscreen-changed',
                                                isFullscreen: false
                                            }}, '*');
                                        }}
                                    }}, 500);
                                    
                                    // Также слушаем сообщения от нового окна для закрытия
                                    window.addEventListener('message', function(closeEvent) {{
                                        if (closeEvent.data && closeEvent.data.type === 'close-fullscreen-window') {{
                                            if (newWindow && !newWindow.closed) {{
                                                newWindow.close();
                                            }}
                                        }}
                                    }});
                                    
                                    return; // Выходим, так как используем новое окно - НЕ применяем CSS к iframe
                                }} else {{
                                    console.warn('[EMBED] Failed to open new window (popup blocked?), falling back to CSS approach');
                                    // Fallback на CSS подход, если popup заблокирован
                                }}
                            }}
                        }}
                        
                        // Для десктопов и если popup заблокирован используем CSS подход
                        // ВАЖНО: Для мобильных устройств этот код выполняется только если popup заблокирован
                        console.log('[EMBED] Using CSS fullscreen approach');
                        enterFullscreenCSS(iframe, requestedScreenWidth, requestedScreenHeight);
                        
                        // Также пробуем использовать стандартный Fullscreen API как дополнение
                        // (не для iOS, так как там он может не работать)
                        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
                        if (!isIOS && iframe.requestFullscreen) {{
                            iframe.requestFullscreen().then(() => {{
                                console.log('[EMBED] Iframe entered fullscreen via API (in addition to CSS)');
                            }}).catch(err => {{
                                console.log('[EMBED] Fullscreen API not available, using CSS only:', err);
                            }});
                        }}
                        
                        // Отправляем подтверждение viewer с размерами экрана
                        iframe.contentWindow.postMessage({{
                            type: 'fullscreen-response',
                            success: true,
                            screenWidth: requestedScreenWidth,
                            screenHeight: requestedScreenHeight
                        }}, '*');
                    }} else if (event.data.action === 'exit') {{
                        // Выходим из полноэкранного режима
                        console.log('[EMBED] Exiting fullscreen mode for iframe');
                        
                        // Для iOS пробуем использовать стандартный API для выхода
                        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
                        
                        if (isIOS) {{
                            // Пробуем использовать webkitExitFullscreen для iOS
                            if (document.webkitExitFullscreen) {{
                                try {{
                                    document.webkitExitFullscreen();
                                    console.log('[EMBED] iOS: webkitExitFullscreen called');
                                }} catch (e) {{
                                    console.error('[EMBED] iOS: webkitExitFullscreen failed:', e);
                                    exitFullscreenCSS(iframe);
                                }}
                            }} else if (document.exitFullscreen) {{
                                document.exitFullscreen().catch(() => {{
                                    exitFullscreenCSS(iframe);
                                }});
                            }} else {{
                                exitFullscreenCSS(iframe);
                            }}
                            iframe.contentWindow.postMessage({{ type: 'fullscreen-response', success: true }}, '*');
                        }} else {{
                            // Пробуем использовать стандартный Fullscreen API
                            if (document.exitFullscreen) {{
                                document.exitFullscreen().catch(() => {{
                                    exitFullscreenCSS(iframe);
                                }});
                            }} else if (document.webkitExitFullscreen) {{
                                document.webkitExitFullscreen();
                            }} else if (document.mozCancelFullScreen) {{
                                document.mozCancelFullScreen();
                            }} else if (document.msExitFullscreen) {{
                                document.msExitFullscreen();
                            }} else {{
                                exitFullscreenCSS(iframe);
                            }}
                            iframe.contentWindow.postMessage({{ type: 'fullscreen-response', success: true }}, '*');
                        }}
                    }}
                }}
            }});
            
            // КРИТИЧЕСКИ ВАЖНО: Для мобильных устройств перемещаем iframe в body напрямую
            // Это обходит ограничения контейнера Tilda и позволяет iframe разворачиваться на весь экран
            function enterFullscreenCSS(iframe, screenWidthParam, screenHeightParam) {{
                console.log('[EMBED] Using CSS fullscreen approach');
                console.log('[EMBED] Target screen size:', screenWidthParam, 'x', screenHeightParam);
                console.log('[EMBED] Current iframe size:', iframe.offsetWidth, 'x', iframe.offsetHeight);
                console.log('[EMBED] Window size:', window.innerWidth, 'x', window.innerHeight);
                console.log('[EMBED] Document size:', document.documentElement.clientWidth, 'x', document.documentElement.clientHeight);
                
                // Если размеры не переданы, определяем их
                let screenWidth = screenWidthParam;
                let screenHeight = screenHeightParam;
                
                if (!screenWidth || !screenHeight) {{
                    const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
                    const screenW = window.screen.width || 0;
                    const screenH = window.screen.height || 0;
                    
                    if (isIOS) {{
                        // Для iOS определяем ориентацию
                        let isLandscape = false;
                        if (window.orientation !== undefined) {{
                            isLandscape = Math.abs(window.orientation) === 90;
                        }} else {{
                            isLandscape = screenW > screenH;
                        }}
                        
                        if (isLandscape) {{
                            screenWidth = Math.max(screenW, screenH);
                            screenHeight = Math.min(screenW, screenH);
                        }} else {{
                            screenWidth = Math.min(screenW, screenH);
                            screenHeight = Math.max(screenW, screenH);
                        }}
                    }} else {{
                        screenWidth = window.innerWidth || screenW;
                        screenHeight = window.innerHeight || screenH;
                    }}
                }}
                
                console.log('[EMBED] Final screen size:', screenWidth, 'x', screenHeight);
                
                // КРИТИЧЕСКИ ВАЖНО: Для мобильных устройств перемещаем iframe в body напрямую
                // Это обходит все ограничения родительских контейнеров (Tilda и т.д.)
                const isMobile = /iPhone|iPad|iPod|Android|Mobile|BlackBerry|Windows Phone|Opera Mini|Palm/i.test(navigator.userAgent);
                
                if (isMobile && iframe.parentElement !== document.body) {{
                    console.log('[EMBED] Mobile device detected, moving iframe to body to bypass container restrictions');
                    // Сохраняем ссылку на оригинальный родитель для восстановления
                    if (!window.originalIframeParent) {{
                        window.originalIframeParent = iframe.parentElement;
                        window.originalIframeNextSibling = iframe.nextSibling;
                    }}
                    // Перемещаем iframe в body
                    document.body.appendChild(iframe);
                    console.log('[EMBED] Iframe moved to body');
                }}
                
                // КРИТИЧЕСКИ ВАЖНО: сначала устанавливаем body и html на весь экран
                // Используем реальные размеры экрана в пикселях через setProperty для гарантированного применения
                // Это должно быть сделано ДО изменения родительских элементов iframe
                document.body.style.setProperty('position', 'fixed', 'important');
                document.body.style.setProperty('top', '0', 'important');
                document.body.style.setProperty('left', '0', 'important');
                document.body.style.setProperty('right', '0', 'important');
                document.body.style.setProperty('bottom', '0', 'important');
                document.body.style.setProperty('width', screenWidth + 'px', 'important');
                document.body.style.setProperty('height', screenHeight + 'px', 'important');
                document.body.style.setProperty('max-width', screenWidth + 'px', 'important');
                document.body.style.setProperty('max-height', screenHeight + 'px', 'important');
                document.body.style.setProperty('min-width', screenWidth + 'px', 'important');
                document.body.style.setProperty('min-height', screenHeight + 'px', 'important');
                document.body.style.setProperty('margin', '0', 'important');
                document.body.style.setProperty('padding', '0', 'important');
                document.body.style.setProperty('overflow', 'hidden', 'important');
                document.body.style.setProperty('z-index', '999997', 'important');
                
                document.documentElement.style.setProperty('position', 'fixed', 'important');
                document.documentElement.style.setProperty('top', '0', 'important');
                document.documentElement.style.setProperty('left', '0', 'important');
                document.documentElement.style.setProperty('right', '0', 'important');
                document.documentElement.style.setProperty('bottom', '0', 'important');
                document.documentElement.style.setProperty('width', screenWidth + 'px', 'important');
                document.documentElement.style.setProperty('height', screenHeight + 'px', 'important');
                document.documentElement.style.setProperty('max-width', screenWidth + 'px', 'important');
                document.documentElement.style.setProperty('max-height', screenHeight + 'px', 'important');
                document.documentElement.style.setProperty('min-width', screenWidth + 'px', 'important');
                document.documentElement.style.setProperty('min-height', screenHeight + 'px', 'important');
                document.documentElement.style.setProperty('margin', '0', 'important');
                document.documentElement.style.setProperty('padding', '0', 'important');
                document.documentElement.style.setProperty('overflow', 'hidden', 'important');
                
                // Ищем и изменяем размеры всех родительских элементов iframe
                // ВАЖНО: также ищем элементы с ограничениями (max-width, max-height, overflow)
                let parent = iframe.parentElement;
                const parentsToModify = [];
                const allElementsToModify = [];
                
                while (parent && parent !== document.body && parent !== document.documentElement) {{
                    parentsToModify.push(parent);
                    console.log('[EMBED] Found parent element:', parent.tagName, parent.className, 'size:', parent.offsetWidth, 'x', parent.offsetHeight);
                    parent = parent.parentElement;
                }}
                
                // Также ищем все элементы с ограничениями размеров, которые могут мешать fullscreen
                // Это особенно важно для контейнеров Tilda
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {{
                    const style = window.getComputedStyle(el);
                    const hasMaxWidth = style.maxWidth && style.maxWidth !== 'none' && style.maxWidth !== '100%';
                    const hasMaxHeight = style.maxHeight && style.maxHeight !== 'none' && style.maxHeight !== '100%';
                    const hasOverflow = style.overflow !== 'visible' && style.overflow !== 'unset';
                    const hasPosition = style.position === 'relative' || style.position === 'absolute';
                    
                    // Если элемент имеет ограничения и находится в пути к iframe, добавляем его
                    if ((hasMaxWidth || hasMaxHeight || hasOverflow || hasPosition) && 
                        (iframe.contains(el) || el.contains(iframe) || parentsToModify.includes(el))) {{
                        if (!allElementsToModify.includes(el) && !parentsToModify.includes(el)) {{
                            allElementsToModify.push(el);
                        }}
                    }}
                }});
                
                // Сохраняем оригинальные стили родительских элементов
                if (!window.fullscreenParentStyles) {{
                    window.fullscreenParentStyles = new Map();
                }}
                
                // Изменяем размеры всех родительских элементов
                parentsToModify.forEach((parentEl, index) => {{
                    if (!window.fullscreenParentStyles.has(parentEl)) {{
                        window.fullscreenParentStyles.set(parentEl, {{
                            position: parentEl.style.position,
                            width: parentEl.style.width,
                            height: parentEl.style.height,
                            maxWidth: parentEl.style.maxWidth,
                            maxHeight: parentEl.style.maxHeight,
                            overflow: parentEl.style.overflow,
                            margin: parentEl.style.margin,
                            padding: parentEl.style.padding,
                            zIndex: parentEl.style.zIndex
                        }});
                    }}
                    
                    // КРИТИЧЕСКИ ВАЖНО: используем position: fixed для выхода из потока документа
                    // Используем реальные размеры экрана в пикселях через setProperty для гарантированного применения
                    parentEl.style.setProperty('position', 'fixed', 'important');
                    parentEl.style.setProperty('top', '0', 'important');
                    parentEl.style.setProperty('left', '0', 'important');
                    parentEl.style.setProperty('right', '0', 'important');
                    parentEl.style.setProperty('bottom', '0', 'important');
                    parentEl.style.setProperty('width', screenWidth + 'px', 'important');
                    parentEl.style.setProperty('height', screenHeight + 'px', 'important');
                    parentEl.style.setProperty('max-width', screenWidth + 'px', 'important');
                    parentEl.style.setProperty('max-height', screenHeight + 'px', 'important');
                    parentEl.style.setProperty('min-width', screenWidth + 'px', 'important');
                    parentEl.style.setProperty('min-height', screenHeight + 'px', 'important');
                    parentEl.style.setProperty('overflow', 'visible', 'important');
                    parentEl.style.setProperty('margin', '0', 'important');
                    parentEl.style.setProperty('padding', '0', 'important');
                    parentEl.style.setProperty('z-index', '999998', 'important');
                }});
                
                // Изменяем элементы с ограничениями (контейнеры Tilda и т.д.)
                allElementsToModify.forEach((el) => {{
                    if (!window.fullscreenParentStyles.has(el)) {{
                        window.fullscreenParentStyles.set(el, {{
                            position: el.style.position,
                            width: el.style.width,
                            height: el.style.height,
                            maxWidth: el.style.maxWidth,
                            maxHeight: el.style.maxHeight,
                            overflow: el.style.overflow,
                            margin: el.style.margin,
                            padding: el.style.padding
                        }});
                    }}
                    
                    // Убираем ограничения размеров
                    el.style.setProperty('max-width', 'none', 'important');
                    el.style.setProperty('max-height', 'none', 'important');
                    el.style.setProperty('overflow', 'visible', 'important');
                }});
                
                // Делаем iframe на весь экран используя реальные размеры экрана в пикселях
                // Используем setProperty для гарантированного применения стилей
                iframe.style.setProperty('position', 'fixed', 'important');
                iframe.style.setProperty('top', '0', 'important');
                iframe.style.setProperty('left', '0', 'important');
                iframe.style.setProperty('right', '0', 'important');
                iframe.style.setProperty('bottom', '0', 'important');
                iframe.style.setProperty('width', screenWidth + 'px', 'important');
                iframe.style.setProperty('height', screenHeight + 'px', 'important');
                iframe.style.setProperty('max-width', screenWidth + 'px', 'important');
                iframe.style.setProperty('max-height', screenHeight + 'px', 'important');
                iframe.style.setProperty('min-width', screenWidth + 'px', 'important');
                iframe.style.setProperty('min-height', screenHeight + 'px', 'important');
                iframe.style.setProperty('z-index', '999999', 'important');
                iframe.style.setProperty('border', 'none', 'important');
                iframe.style.setProperty('margin', '0', 'important');
                iframe.style.setProperty('padding', '0', 'important');
                iframe.style.setProperty('background-color', '#000', 'important');
                iframe.style.setProperty('display', 'block', 'important');
                
                // Повторно применяем стили к html после изменения всех родительских элементов
                // Это гарантирует, что html получит правильные размеры
                setTimeout(() => {{
                    document.documentElement.style.setProperty('position', 'fixed', 'important');
                    document.documentElement.style.setProperty('top', '0', 'important');
                    document.documentElement.style.setProperty('left', '0', 'important');
                    document.documentElement.style.setProperty('right', '0', 'important');
                    document.documentElement.style.setProperty('bottom', '0', 'important');
                    document.documentElement.style.setProperty('width', screenWidth + 'px', 'important');
                    document.documentElement.style.setProperty('height', screenHeight + 'px', 'important');
                    document.documentElement.style.setProperty('max-width', screenWidth + 'px', 'important');
                    document.documentElement.style.setProperty('max-height', screenHeight + 'px', 'important');
                    document.documentElement.style.setProperty('min-width', screenWidth + 'px', 'important');
                    document.documentElement.style.setProperty('min-height', screenHeight + 'px', 'important');
                    document.documentElement.style.setProperty('margin', '0', 'important');
                    document.documentElement.style.setProperty('padding', '0', 'important');
                    document.documentElement.style.setProperty('overflow', 'hidden', 'important');
                    
                    console.log('[EMBED] Re-applied html styles, html size:', document.documentElement.offsetWidth, 'x', document.documentElement.offsetHeight);
                }}, 50);
                
                // Отправляем размеры экрана в viewer через postMessage
                // Это позволит viewer правильно масштабировать изображение
                setTimeout(() => {{
                    if (iframe.contentWindow) {{
                        iframe.contentWindow.postMessage({{
                            type: 'fullscreen-screen-size',
                            width: screenWidth,
                            height: screenHeight
                        }}, '*');
                    }}
                }}, 100);
                
                // Body и html уже изменены выше, но убеждаемся что они остаются фиксированными
                // (это дублирование для надежности, но не критично)
                
                // Скрываем loading
                const loading = document.getElementById('loading');
                if (loading) {{
                    loading.style.display = 'none';
                }}
                
                // Проверяем результат через небольшую задержку
                setTimeout(() => {{
                    console.log('[EMBED] After fullscreen CSS, iframe size:', iframe.offsetWidth, 'x', iframe.offsetHeight);
                    console.log('[EMBED] After fullscreen CSS, iframe computed style:', window.getComputedStyle(iframe).width, 'x', window.getComputedStyle(iframe).height);
                    console.log('[EMBED] After fullscreen CSS, body size:', document.body.offsetWidth, 'x', document.body.offsetHeight);
                    console.log('[EMBED] After fullscreen CSS, html size:', document.documentElement.clientWidth, 'x', document.documentElement.clientHeight);
                }}, 200);
            }}
            
            function exitFullscreenCSS(iframe) {{
                console.log('[EMBED] Exiting CSS fullscreen');
                
                // КРИТИЧЕСКИ ВАЖНО: Если iframe был перемещен в body (для мобильных), возвращаем его обратно
                if (window.originalIframeParent && iframe.parentElement === document.body) {{
                    console.log('[EMBED] Restoring iframe to original parent');
                    if (window.originalIframeNextSibling) {{
                        window.originalIframeParent.insertBefore(iframe, window.originalIframeNextSibling);
                    }} else {{
                        window.originalIframeParent.appendChild(iframe);
                    }}
                    window.originalIframeParent = null;
                    window.originalIframeNextSibling = null;
                }}
                
                // Восстанавливаем стили родительских элементов
                if (window.fullscreenParentStyles) {{
                    let parent = iframe.parentElement;
                    while (parent && parent !== document.body && parent !== document.documentElement) {{
                        if (window.fullscreenParentStyles.has(parent)) {{
                            const styles = window.fullscreenParentStyles.get(parent);
                            parent.style.position = styles.position || '';
                            parent.style.width = styles.width || '';
                            parent.style.height = styles.height || '';
                            parent.style.maxWidth = styles.maxWidth || '';
                            parent.style.maxHeight = styles.maxHeight || '';
                            parent.style.overflow = styles.overflow || '';
                            parent.style.margin = styles.margin || '';
                            parent.style.padding = styles.padding || '';
                            parent.style.zIndex = styles.zIndex || '';
                        }}
                        parent = parent.parentElement;
                    }}
                    window.fullscreenParentStyles.clear();
                }}
                
                // Очищаем все стили iframe
                iframe.style.cssText = '';
                iframe.style.width = '100%';
                iframe.style.height = '100%';
                
                // Восстанавливаем body и html
                document.body.style.cssText = '';
                document.documentElement.style.cssText = '';
            }}
            
            // Обработка событий полноэкранного режима
            document.addEventListener('fullscreenchange', function() {{
                const iframe = document.getElementById('viewerFrame');
                if (!iframe) return;
                
                if (!document.fullscreenElement) {{
                    // Выходим из полноэкранного режима
                    exitFullscreenCSS(iframe);
                    // Отправляем сообщение viewer о выходе
                    iframe.contentWindow.postMessage({{ type: 'fullscreen-changed', isFullscreen: false }}, '*');
                }}
            }});
            
            document.addEventListener('webkitfullscreenchange', function() {{
                const iframe = document.getElementById('viewerFrame');
                if (!iframe) return;
                if (!document.webkitFullscreenElement) {{
                    exitFullscreenCSS(iframe);
                    iframe.contentWindow.postMessage({{ type: 'fullscreen-changed', isFullscreen: false }}, '*');
                }}
            }});
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