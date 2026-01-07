"""
Secure Content Service - Main Application
Сервис для защищенного показа контента с водяными знаками
"""
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.api import router
from app.api import viewer as viewer_module
from app.models.database import init_db

logger = logging.getLogger(__name__)

# Инициализация БД при старте
init_db()

app = FastAPI(
    title="Secure Content Service",
    description="Сервис для защищенного показа PDF/PPT контента с водяными знаками",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware для добавления заголовков безопасности для iframe
class FrameOptionsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Разрешаем встраивание в iframe для embed и viewer endpoints
        path = str(request.url.path)
        if "/embed" in path or "/viewer" in path:
            # Убираем X-Frame-Options для разрешения встраивания
            if "X-Frame-Options" in response.headers:
                del response.headers["X-Frame-Options"]
            # Разрешаем встраивание через Content-Security-Policy
            response.headers["Content-Security-Policy"] = "frame-ancestors *;"
        return response

app.add_middleware(FrameOptionsMiddleware)

# Exception handler для логирования всех ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений для логирования"""
    error_trace = traceback.format_exc()
    logger.error(f"Unhandled exception: {error_trace}")
    print(f"[ERROR] Unhandled exception: {error_trace}")
    
    # Если это HTTPException, возвращаем его как есть
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail)}
        )
    
    # Для остальных ошибок возвращаем 500
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Подключение роутеров
app.include_router(router, prefix="/api")

# Viewer доступен как по /api/viewer, так и по /viewer (для удобства)
# Подключаем viewer роутер с префиксом /api/viewer для единообразия API
app.include_router(viewer_module.router, prefix="/api/viewer", tags=["viewer"])
# Также подключаем по /viewer для обратной совместимости
app.include_router(viewer_module.router, prefix="/viewer", tags=["viewer-public"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "service": "secure-content-service"})


@app.get("/")
async def root():
    """Корневой endpoint"""
    return JSONResponse({
        "service": "Secure Content Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
