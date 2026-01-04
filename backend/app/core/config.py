"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator
import os


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Безопасность
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # База данных
    DATABASE_URL: str = "sqlite:///./data/database.db"
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:8080"
    
    # Разрешенные домены для встраивания (проверка Referer)
    ALLOWED_EMBED_DOMAINS: Union[str, List[str]] = ""
    
    # Требовать проверку Referer для viewer (защита от прямого доступа)
    REQUIRE_REFERER_CHECK: Union[str, bool] = False
    
    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    @field_validator('ALLOWED_EMBED_DOMAINS', mode='before')
    @classmethod
    def parse_allowed_embed_domains(cls, v):
        if isinstance(v, str):
            return [domain.strip() for domain in v.split(',') if domain.strip()]
        return v
    
    @field_validator('REQUIRE_REFERER_CHECK', mode='before')
    @classmethod
    def parse_bool(cls, v):
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return bool(v)
    
    # Файлы
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "uploads"
    CACHE_DIR: str = "cache"
    DATA_DIR: str = "data"
    STATIC_WATERMARK_DIR: str = "static_watermarks"
    
    # Водяные знаки
    DEFAULT_WATERMARK_OPACITY: float = 0.25
    DEFAULT_WATERMARK_FONT_SIZE: int = 48
    DEFAULT_WATERMARK_COLOR_R: int = 128
    DEFAULT_WATERMARK_COLOR_G: int = 128
    DEFAULT_WATERMARK_COLOR_B: int = 128
    
    # Конвертация
    PDF_DPI: int = 200
    PPT_DPI: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Создаем необходимые директории
for dir_path in [
    settings.UPLOAD_DIR,
    settings.CACHE_DIR,
    settings.DATA_DIR,
    settings.STATIC_WATERMARK_DIR
]:
    os.makedirs(dir_path, exist_ok=True)
