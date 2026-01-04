"""
API для административных функций
"""
import json
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.database import get_db, Document, User, DocumentAccess, GlobalWatermarkSettings
from app.models.schemas import AccessGrant, WatermarkSettings
from datetime import datetime

router = APIRouter()

# Templates для админки
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


@router.get("/", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Админ-панель"""
    if templates:
        return templates.TemplateResponse("admin.html", {"request": request})
    else:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("""
        <html>
        <head><title>Admin Panel</title></head>
        <body>
            <h1>Admin Panel</h1>
            <p>Шаблон admin.html не найден. Убедитесь, что файл находится в frontend/templates/admin.html</p>
        </body>
        </html>
        """)


@router.post("/documents/{document_id}/access")
async def grant_access(
    document_id: int,
    user_emails: str = Form(...),
    db: Session = Depends(get_db)
):
    """Предоставление доступа пользователям к документу"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    email_list = [e.strip() for e in user_emails.split('\n') if e.strip()]
    results = {}
    
    for email in email_list:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            results[email] = False
            continue
        
        # Проверяем, нет ли уже доступа
        existing = db.query(DocumentAccess).filter(
            DocumentAccess.document_id == document_id,
            DocumentAccess.user_id == user.id
        ).first()
        
        if existing:
            results[email] = True  # Доступ уже есть
            continue
        
        # Создаем доступ
        access = DocumentAccess(
            document_id=document_id,
            user_id=user.id,
            granted_by="admin"
        )
        db.add(access)
        results[email] = True
    
    db.commit()
    
    return {
        "success": sum(1 for v in results.values() if v),
        "failed": sum(1 for v in results.values() if not v),
        "results": results
    }


@router.get("/documents/{document_id}/access")
async def get_document_access(document_id: int, db: Session = Depends(get_db)):
    """Получение списка пользователей с доступом к документу"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    accesses = db.query(DocumentAccess).filter(
        DocumentAccess.document_id == document_id
    ).all()
    
    users_with_access = []
    for access in accesses:
        user = db.query(User).filter(User.id == access.user_id).first()
        if user:
            users_with_access.append({
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "granted_at": access.granted_at.isoformat(),
                "granted_by": access.granted_by
            })
    
    return users_with_access


@router.delete("/documents/{document_id}/access/{user_email}")
async def revoke_access(
    document_id: int,
    user_email: str,
    db: Session = Depends(get_db)
):
    """Отзыв доступа пользователя к документу"""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    access = db.query(DocumentAccess).filter(
        DocumentAccess.document_id == document_id,
        DocumentAccess.user_id == user.id
    ).first()
    
    if not access:
        raise HTTPException(status_code=404, detail="Доступ не найден")
    
    db.delete(access)
    db.commit()
    
    return {"status": "success"}


@router.put("/watermark/global")
async def update_global_watermark(
    watermark_settings: str = Form(...),
    db: Session = Depends(get_db)
):
    """Обновление глобальных настроек водяных знаков (для всех документов)"""
    try:
        # Парсим JSON настройки
        settings_dict = json.loads(watermark_settings)
        # Валидируем через Pydantic
        validated_settings = WatermarkSettings(**settings_dict)
        
        # Получаем или создаем глобальные настройки
        global_settings = db.query(GlobalWatermarkSettings).first()
        if not global_settings:
            global_settings = GlobalWatermarkSettings(
                settings_json=json.dumps(validated_settings.dict()),
                updated_at=datetime.utcnow()
            )
            db.add(global_settings)
        else:
            global_settings.settings_json = json.dumps(validated_settings.dict())
            global_settings.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Очищаем кеш изображений с водяными знаками для ВСЕХ документов
        import os
        import shutil
        from app.core.config import settings
        
        cache_dir = settings.CACHE_DIR
        if os.path.exists(cache_dir):
            for doc_hash_dir in os.listdir(cache_dir):
                doc_cache_path = os.path.join(cache_dir, doc_hash_dir)
                if os.path.isdir(doc_cache_path):
                    for filename in os.listdir(doc_cache_path):
                        if filename.startswith("watermarked_"):
                            file_path = os.path.join(doc_cache_path, filename)
                            try:
                                os.remove(file_path)
                            except:
                                pass
        
        return {
            "status": "success",
            "message": "Глобальные настройки водяных знаков обновлены",
            "watermark_settings": validated_settings.dict()
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка валидации: {str(e)}")


@router.get("/watermark/global")
async def get_global_watermark(db: Session = Depends(get_db)):
    """Получение глобальных настроек водяных знаков"""
    global_settings = db.query(GlobalWatermarkSettings).first()
    
    if global_settings and global_settings.settings_json:
        try:
            settings_dict = json.loads(global_settings.settings_json)
            return settings_dict
        except:
            pass
    
    # Возвращаем настройки по умолчанию
    return WatermarkSettings().dict()


@router.get("/watermark/preview")
async def preview_watermark(
    request: Request,
    db: Session = Depends(get_db)
):
    """Предпросмотр водяных знаков на тестовом изображении"""
    from fastapi.responses import FileResponse
    from PIL import Image, ImageDraw, ImageFont
    import io
    from app.services.watermark import WatermarkService
    
    # Получаем глобальные настройки
    global_settings = db.query(GlobalWatermarkSettings).first()
    watermark_settings = WatermarkSettings()
    if global_settings and global_settings.settings_json:
        try:
            settings_dict = json.loads(global_settings.settings_json)
            watermark_settings = WatermarkSettings(**settings_dict)
        except:
            pass
    
    # Создаем тестовое изображение (белый лист A4)
    width, height = 800, 1131  # A4 пропорции
    test_image = Image.new('RGB', (width, height), color='white')
    
    # Добавляем тестовый текст для визуализации
    draw = ImageDraw.Draw(test_image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    draw.text((50, 50), "Тестовая страница для предпросмотра водяных знаков", fill=(0, 0, 0), font=font)
    draw.text((50, 100), "Это пример того, как будут выглядеть водяные знаки", fill=(0, 0, 0), font=font)
    
    # Получаем путь к статическому водяному знаку, если он указан
    static_watermark_path = None
    if watermark_settings.static_watermark_enabled and watermark_settings.static_watermark_id:
        from app.models.database import StaticWatermark
        static_wm = db.query(StaticWatermark).filter(
            StaticWatermark.id == watermark_settings.static_watermark_id,
            StaticWatermark.is_active == True
        ).first()
        if static_wm:
            import os
            if os.path.exists(static_wm.file_path):
                static_watermark_path = static_wm.file_path
    
    # Устанавливаем seed для предпросмотра
    if not hasattr(watermark_settings, 'random_seed') or not watermark_settings.random_seed:
        watermark_settings.random_seed = "preview_test_seed"
    
    # Применяем водяные знаки с тестовыми данными
    watermarked_image = WatermarkService.apply_watermarks(
        test_image,
        watermark_settings,
        user_email="test@example.com",
        user_id="123",
        ip_address="192.168.1.100",
        page_number=1,
        static_watermark_path=static_watermark_path
    )
    
    # Сохраняем в память
    img_io = io.BytesIO()
    watermarked_image.save(img_io, 'PNG', quality=95)
    img_io.seek(0)
    
    # Возвращаем изображение
    from fastapi.responses import StreamingResponse
    return StreamingResponse(io.BytesIO(img_io.read()), media_type="image/png")
