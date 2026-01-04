"""
Pydantic схемы для валидации данных
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class WatermarkSettings(BaseModel):
    """Настройки водяных знаков"""
    # Статический водяной знак
    static_watermark_enabled: bool = True
    static_watermark_id: Optional[int] = None
    static_watermark_scale: float = 0.2  # Размер относительно страницы
    
    # Динамический водяной знак
    dynamic_watermark_enabled: bool = True
    show_user_email: bool = True
    show_user_id: bool = False
    show_ip_address: bool = True
    show_timestamp: bool = False
    show_page_number: bool = False
    custom_text: str = ""
    
    # Стиль
    opacity: float = 0.25
    font_size: int = 48
    color_r: int = 128
    color_g: int = 128
    color_b: int = 128
    
    # Позиционирование (для обратной совместимости)
    position: str = "center"  # center, top-left, top-right, bottom-left, bottom-right
    
    # Случайное размещение динамического водяного знака (реалтайм анимация)
    random_positions_enabled: bool = True  # Включить случайное размещение
    positions_count: int = 5  # Количество позиций водяного знака на странице
    animation_speed: int = 2000  # Скорость анимации (мс на переход между позициями)
    random_seed: Optional[str] = None  # Seed для детерминированного рандома (обычно user_id или session_token)
    
    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    """Создание документа"""
    name: str
    watermark_settings: Optional[WatermarkSettings] = None


class DocumentResponse(BaseModel):
    """Ответ с информацией о документе"""
    id: int
    name: str
    file_type: str
    total_pages: int
    access_token: str
    created_at: datetime
    watermark_settings: Optional[dict] = None
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Создание пользователя"""
    email: EmailStr
    name: Optional[str] = None


class UserResponse(BaseModel):
    """Ответ с информацией о пользователе"""
    id: int
    email: str
    name: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class AccessGrant(BaseModel):
    """Предоставление доступа"""
    user_emails: List[str]
    document_id: int


class ViewerTokenResponse(BaseModel):
    """Ответ с токеном для просмотра"""
    viewer_token: str
    viewer_url: str
    expires_at: datetime
