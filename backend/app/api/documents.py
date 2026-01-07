"""
API для работы с документами
"""
import os
import json
import hashlib
import secrets
import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List
from app.models.database import get_db, Document, User, DocumentAccess, ViewingSession
from app.models.schemas import DocumentCreate, DocumentResponse, WatermarkSettings
from app.services.converter import DocumentConverter
from app.services.watermark import WatermarkService
from app.core.config import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(None),
    watermark_settings: str = Form(None),
    db: Session = Depends(get_db)
):
    """Загрузка документа"""
    try:
        # Проверка типа файла
        if not file.filename:
            raise HTTPException(status_code=400, detail="Имя файла не указано")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.pdf', '.ppt', '.pptx']:
            raise HTTPException(status_code=400, detail="Поддерживаются только PDF, PPT, PPTX файлы")
        
        # Чтение файла
        contents = await file.read()
        
        if len(contents) > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Файл слишком большой")
        
        # Генерация хеша
        file_hash = hashlib.md5(contents).hexdigest()
        
        # Проверка на дубликат
        existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing_doc:
            watermark_settings = None
            if existing_doc.watermark_settings:
                try:
                    watermark_settings = json.loads(existing_doc.watermark_settings)
                except:
                    pass
            return DocumentResponse(
                id=existing_doc.id,
                name=existing_doc.name,
                file_type=existing_doc.file_type,
                total_pages=existing_doc.total_pages,
                access_token=existing_doc.access_token,
                created_at=existing_doc.created_at,
                watermark_settings=watermark_settings
            )
        
        # Сохранение файла
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_")
        file_path = os.path.join(settings.UPLOAD_DIR, f"{file_hash}_{safe_filename}")
        
        # Создаем директорию, если её нет
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(contents)
        
        # Конвертация в изображения
        file_type = file_ext[1:]  # убираем точку
        output_dir = os.path.join(settings.CACHE_DIR, file_hash)
        
        # Создаем директорию для кеша, если её нет
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            images = DocumentConverter.convert_to_images(file_path, file_type, output_dir)
            total_pages = len(images)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Conversion error: {error_trace}")
            print(f"[ERROR] Conversion error: {error_trace}")
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Ошибка конвертации: {str(e)}")
        
        # Парсинг настроек водяных знаков
        watermark_config = None
        if watermark_settings:
            try:
                watermark_config = json.loads(watermark_settings)
            except Exception as e:
                logger.warning(f"Failed to parse watermark settings: {e}")
                print(f"[WARN] Failed to parse watermark settings: {e}")
                pass
        
        if not watermark_config:
            watermark_config = WatermarkSettings().dict()
        
        # Создание документа в БД
        access_token = secrets.token_urlsafe(32)
        
        doc = Document(
            name=name or safe_filename,
            file_path=file_path,
            file_hash=file_hash,
            file_type=file_type,
            total_pages=total_pages,
            access_token=access_token,
            watermark_settings=json.dumps(watermark_config) if watermark_config else None,
            created_by="api"
        )
        
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        return DocumentResponse(
            id=doc.id,
            name=doc.name,
            file_type=doc.file_type,
            total_pages=doc.total_pages,
            access_token=doc.access_token,
            created_at=doc.created_at,
            watermark_settings=watermark_config
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Upload error: {error_trace}")
        print(f"[ERROR] Upload error: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(db: Session = Depends(get_db)):
    """Список всех документов"""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    result = []
    for doc in docs:
        watermark_settings = None
        if doc.watermark_settings:
            watermark_settings = json.loads(doc.watermark_settings)
        result.append(DocumentResponse(
            id=doc.id,
            name=doc.name,
            file_type=doc.file_type,
            total_pages=doc.total_pages,
            access_token=doc.access_token,
            created_at=doc.created_at,
            watermark_settings=watermark_settings
        ))
    return result


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Удаление документа"""
    import shutil
    from app.models.database import ViewingSession, DocumentAccess
    
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    # Удаляем связанные сессии
    db.query(ViewingSession).filter(ViewingSession.document_id == document_id).delete()
    
    # Удаляем связанные доступы
    db.query(DocumentAccess).filter(DocumentAccess.document_id == document_id).delete()
    
    # Удаляем файл документа
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except:
            pass
    
    # Удаляем кеш изображений
    cache_dir = os.path.join(settings.CACHE_DIR, doc.file_hash)
    if os.path.exists(cache_dir):
        try:
            shutil.rmtree(cache_dir)
        except:
            pass
    
    # Удаляем документ из БД
    db.delete(doc)
    db.commit()
    
    return {"status": "success", "message": "Документ удален"}


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Получение информации о документе"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    watermark_settings = None
    if doc.watermark_settings:
        watermark_settings = json.loads(doc.watermark_settings)
    
    return DocumentResponse(
        id=doc.id,
        name=doc.name,
        file_type=doc.file_type,
        total_pages=doc.total_pages,
        access_token=doc.access_token,
        created_at=doc.created_at,
        watermark_settings=watermark_settings
    )


@router.get("/{document_id}/page/{page_number}")
async def get_page_image(
    document_id: int,
    page_number: int,
    viewer_token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Получение изображения страницы с водяными знаками"""
    # Проверка Referer (защита от прямого доступа к изображениям)
    from urllib.parse import urlparse
    from app.core.config import settings
    
    def check_referer_for_images(req: Request) -> bool:
        """Проверка Referer для изображений"""
        if not settings.REQUIRE_REFERER_CHECK:
            return True
        if not settings.ALLOWED_EMBED_DOMAINS:
            return True
        referer = req.headers.get("referer")
        if not referer:
            return False
        try:
            referer_parsed = urlparse(referer)
            referer_domain = referer_parsed.netloc.lower().split(':')[0]  # Убираем порт для сравнения
            request_host = req.url.hostname.lower() if req.url.hostname else ""
            
            # Если Referer указывает на тот же сервер, разрешаем (внутренний запрос из iframe)
            if referer_domain == request_host:
                return True
            
            # Проверяем разрешенные домены
            for allowed_domain in settings.ALLOWED_EMBED_DOMAINS:
                allowed_parsed = urlparse(allowed_domain if allowed_domain.startswith('http') else f'https://{allowed_domain}')
                allowed_domain_clean = allowed_parsed.netloc.lower().replace('www.', '').split(':')[0]
                referer_domain_clean = referer_domain.replace('www.', '')
                if referer_domain_clean == allowed_domain_clean:
                    return True
            return False
        except Exception:
            return False
    
    if not check_referer_for_images(request):
        raise HTTPException(
            status_code=403, 
            detail="Доступ разрешен только с разрешенных доменов"
        )
    
    # Проверка документа
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    if page_number < 1 or page_number > doc.total_pages:
        raise HTTPException(status_code=404, detail="Страница не найдена")
    
    # Проверка viewer_token и получение информации о пользователе
    session = db.query(ViewingSession).filter(ViewingSession.session_token == viewer_token).first()
    if not session:
        raise HTTPException(status_code=403, detail="Сессия недействительна")
    
    if datetime.utcnow() > session.expires_at:
        raise HTTPException(status_code=403, detail="Сессия истекла")
    
    if session.document_id != document_id:
        raise HTTPException(status_code=403, detail="Неверный документ для сессии")
    
    # Получаем информацию о пользователе из сессии (может быть None)
    user_email = session.user.email if session.user else None
    user_id = str(session.user.id) if session.user else None
    
    # Путь к базовому изображению
    base_image_path = os.path.join(
        settings.CACHE_DIR,
        doc.file_hash,
        f"page_{page_number}.png"
    )
    
    if not os.path.exists(base_image_path):
        raise HTTPException(status_code=404, detail="Изображение страницы не найдено")
    
    # Путь к изображению с водяными знаками
    watermarked_path = os.path.join(
        settings.CACHE_DIR,
        doc.file_hash,
        f"watermarked_{viewer_token}_page_{page_number}.png"
    )
    
    # Если изображение с водяными знаками уже существует, возвращаем его
    if os.path.exists(watermarked_path):
        # Читаем файл полностью в память для гарантии правильного Content-Length
        # Это решает проблему ERR_CONTENT_LENGTH_MISMATCH
        with open(watermarked_path, 'rb') as f:
            img_bytes = f.read()
        
        from fastapi import Response
        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={
                "Content-Length": str(len(img_bytes)),
                "Cache-Control": "public, max-age=3600",
                "Accept-Ranges": "bytes"
            }
        )
    
    # Иначе создаем изображение с водяными знаками
    try:
        from PIL import Image
        import json
        from app.models.database import GlobalWatermarkSettings
        
        base_image = Image.open(base_image_path)
        
        # Загружаем глобальные настройки водяных знаков
        watermark_settings = WatermarkSettings()
        global_settings = db.query(GlobalWatermarkSettings).first()
        if global_settings and global_settings.settings_json:
            try:
                settings_dict = json.loads(global_settings.settings_json)
                watermark_settings = WatermarkSettings(**settings_dict)
            except:
                pass
        
        # Получаем путь к статическому водяному знаку, если он указан
        static_watermark_path = None
        if watermark_settings.static_watermark_enabled and watermark_settings.static_watermark_id:
            from app.models.database import StaticWatermark
            static_wm = db.query(StaticWatermark).filter(
                StaticWatermark.id == watermark_settings.static_watermark_id,
                StaticWatermark.is_active == True
            ).first()
            if static_wm and os.path.exists(static_wm.file_path):
                static_watermark_path = static_wm.file_path
        
        # Получаем информацию из сессии (user может быть None в упрощенной версии)
        user_email = session.user.email if session.user else None
        ip_address = session.ip_address or "127.0.0.1"
        
        # Если включена реалтайм анимация динамического водяного знака, не накладываем его на сервере
        # (он будет отрисовываться на клиенте через Canvas)
        apply_dynamic_on_server = True
        if hasattr(watermark_settings, 'random_positions_enabled') and watermark_settings.random_positions_enabled:
            # Если включена анимация, динамический водяной знак не накладываем на сервере
            apply_dynamic_on_server = False
        
        # Временно отключаем динамический водяной знак для применения на сервере, если включена анимация
        original_dynamic_enabled = watermark_settings.dynamic_watermark_enabled
        if not apply_dynamic_on_server:
            watermark_settings.dynamic_watermark_enabled = False
        
        # Устанавливаем seed для детерминированного рандома (чтобы позиции были одинаковыми для одного пользователя)
        if not hasattr(watermark_settings, 'random_seed') or not watermark_settings.random_seed:
            watermark_settings.random_seed = str(session.user_id) if session.user_id else session.session_token
        
        # Применяем водяные знаки (только статический, если динамический отключен для анимации)
        watermarked_image = WatermarkService.apply_watermarks(
            base_image,
            watermark_settings,
            user_email=user_email,
            user_id=str(session.user_id) if session.user_id else None,
            ip_address=ip_address,
            page_number=page_number,
            static_watermark_path=static_watermark_path
        )
        
        # Восстанавливаем настройку
        watermark_settings.dynamic_watermark_enabled = original_dynamic_enabled
        
        # Сохраняем в BytesIO сначала, чтобы получить точный размер
        import io
        img_io = io.BytesIO()
        watermarked_image.save(img_io, 'PNG', quality=95, optimize=True)
        img_bytes = img_io.getvalue()
        img_size = len(img_bytes)
        
        # Сохраняем на диск для кеширования
        try:
            with open(watermarked_path, 'wb') as f:
                f.write(img_bytes)
        except Exception as e:
            print(f"[WARN] Failed to save watermarked image to cache: {e}")
        
        # Возвращаем Response с байтами из памяти - это гарантирует правильный Content-Length
        from fastapi import Response
        return Response(
            content=img_bytes,
            media_type="image/png",
            headers={
                "Content-Length": str(img_size),
                "Cache-Control": "public, max-age=3600",
                "Accept-Ranges": "bytes"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки изображения: {str(e)}")
