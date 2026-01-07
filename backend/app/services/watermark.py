"""
Сервис наложения водяных знаков
"""
import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from typing import Optional
from app.models.schemas import WatermarkSettings
from app.core.config import settings


class WatermarkService:
    """Сервис для наложения водяных знаков"""
    
    @staticmethod
    def apply_watermarks(
        image: Image.Image,
        settings: WatermarkSettings,
        user_email: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        page_number: Optional[int] = None,
        static_watermark_path: Optional[str] = None
    ) -> Image.Image:
        """Применение водяных знаков к изображению"""
        result_image = image.copy()
        
        # Применяем статический водяной знак
        if settings.static_watermark_enabled and static_watermark_path:
            result_image = WatermarkService._apply_static_watermark(
                result_image,
                static_watermark_path,
                settings
            )
        
        # Применяем динамический водяной знак
        if settings.dynamic_watermark_enabled:
            result_image = WatermarkService._apply_dynamic_watermark(
                result_image,
                settings,
                user_email,
                user_id,
                ip_address,
                page_number
            )
        
        return result_image
    
    @staticmethod
    def _apply_static_watermark(
        image: Image.Image,
        watermark_path: str,
        settings: WatermarkSettings
    ) -> Image.Image:
        """Применение статического водяного знака (логотип)"""
        if not os.path.exists(watermark_path):
            return image
        
        try:
            watermark_img = Image.open(watermark_path)
            
            # Конвертируем в RGBA если нужно
            if watermark_img.mode != 'RGBA':
                watermark_img = watermark_img.convert('RGBA')
            
            # Масштабируем водяной знак
            img_width, img_height = image.size
            scale = settings.static_watermark_scale if hasattr(settings, 'static_watermark_scale') else 0.2
            
            new_width = int(img_width * scale)
            new_height = int(watermark_img.height * (new_width / watermark_img.width))
            watermark_img = watermark_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Применяем прозрачность
            opacity = int(255 * settings.opacity)
            alpha = watermark_img.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity / 255))
            watermark_img.putalpha(alpha)
            
            # Позиционируем водяной знак
            position = WatermarkService._calculate_position(
                image.size,
                watermark_img.size,
                settings.position
            )
            
            # Накладываем водяной знак
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            image.paste(watermark_img, position, watermark_img)
            
            # Конвертируем обратно в RGB если нужно
            if image.mode == 'RGBA':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])
                image = rgb_image
            
            return image
            
        except Exception as e:
            print(f"Ошибка применения статического водяного знака: {e}")
            return image
    
    @staticmethod
    def _apply_dynamic_watermark(
        image: Image.Image,
        settings: WatermarkSettings,
        user_email: Optional[str],
        user_id: Optional[str],
        ip_address: Optional[str],
        page_number: Optional[int]
    ) -> Image.Image:
        """Применение динамического водяного знака"""
        # Формируем текст водяного знака
        parts = []
        
        if settings.custom_text:
            parts.append(settings.custom_text)
        
        if settings.show_user_email and user_email:
            parts.append(f"User: {user_email}")
        elif settings.show_user_id and user_id:
            parts.append(f"ID: {user_id}")
        
        if settings.show_ip_address and ip_address:
            parts.append(f"IP: {ip_address}")
        
        if settings.show_page_number and page_number:
            parts.append(f"Page: {page_number}")
        
        if settings.show_timestamp:
            parts.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        if not parts:
            return image
        
        watermark_text = " | ".join(parts)
        
        # Создаем полупрозрачный слой
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Загружаем шрифт
        font = WatermarkService._get_font(settings.font_size)
        
        # Цвет водяного знака
        fill_color = (
            settings.color_r,
            settings.color_g,
            settings.color_b,
            int(255 * settings.opacity)
        )
        
        # Получаем размер текста
        bbox = overlay_draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Определяем, использовать ли случайное размещение
        use_random = getattr(settings, 'random_positions_enabled', True)
        positions_count = getattr(settings, 'positions_count', 5)
        
        if use_random and positions_count > 1:
            # Генерируем случайные позиции
            positions = WatermarkService._generate_random_positions(
                image.size,
                (text_width, text_height),
                positions_count,
                getattr(settings, 'random_seed', None) or user_id or user_email or "default"
            )
            
            # Рисуем водяной знак в каждой позиции
            for pos in positions:
                overlay_draw.text(pos, watermark_text, font=font, fill=fill_color)
        else:
            # Используем старый способ - одна позиция
            position = WatermarkService._calculate_text_position(
                image.size,
                (text_width, text_height),
                settings.position
            )
            overlay_draw.text(position, watermark_text, font=font, fill=fill_color)
        
        # Накладываем водяной знак
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        image = Image.alpha_composite(image, overlay)
        
        # Конвертируем обратно в RGB если нужно
        if image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        
        return image
    
    @staticmethod
    def _generate_random_positions(
        image_size: tuple,
        text_size: tuple,
        count: int,
        seed: str
    ) -> list:
        """Генерация случайных позиций для водяного знака (детерминированный рандом)"""
        import random
        import hashlib
        
        img_width, img_height = image_size
        text_width, text_height = text_size
        
        # Создаем детерминированный рандом на основе seed
        seed_hash = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        rng = random.Random(seed_hash)
        
        # Отступ от краев (минимум 10 пикселей)
        padding = 10
        
        # Вычисляем безопасные границы с учетом размера текста
        # min_x и min_y - минимальные координаты (с отступом)
        min_x = padding
        min_y = padding
        
        # max_x и max_y - максимальные координаты (с учетом размера текста и отступа)
        # Важно: текст должен полностью помещаться, поэтому вычитаем его размер
        max_x = img_width - text_width - padding
        max_y = img_height - text_height - padding
        
        # Проверяем, что есть место для размещения
        if max_x < min_x or max_y < min_y or text_width > img_width or text_height > img_height:
            # Если места мало или текст слишком большой, размещаем в безопасном месте
            # Размещаем в левом верхнем углу с минимальным отступом
            safe_x = max(0, min(padding, img_width - text_width))
            safe_y = max(0, min(padding, img_height - text_height))
            return [(safe_x, safe_y)]
        
        positions = []
        attempts = 0
        max_attempts = count * 50  # Увеличиваем количество попыток
        
        while len(positions) < count and attempts < max_attempts:
            attempts += 1
            # Генерируем случайные координаты в безопасных пределах
            x = rng.uniform(min_x, max_x)
            y = rng.uniform(min_y, max_y)
            
            # Округляем до целых
            x_int = int(x)
            y_int = int(y)
            
            # Строгая проверка: текст должен полностью помещаться в границы изображения
            if (x_int >= 0 and 
                y_int >= 0 and 
                x_int + text_width <= img_width and 
                y_int + text_height <= img_height):
                
                # Проверяем, что позиция не слишком близко к другим
                too_close = False
                min_distance = min(text_width, text_height) * 0.3  # Минимальное расстояние между водяными знаками
                
                for existing_pos in positions:
                    dx = abs(x_int - existing_pos[0])
                    dy = abs(y_int - existing_pos[1])
                    if dx < min_distance and dy < min_distance:
                        too_close = True
                        break
                
                if not too_close:
                    positions.append((x_int, y_int))
        
        # Если не удалось сгенерировать достаточно позиций, добавляем безопасные позиции
        if len(positions) == 0:
            # Пробуем разместить в разных углах
            safe_positions_to_try = [
                (max(0, min(padding, img_width - text_width)), max(0, min(padding, img_height - text_height))),  # top-left
                (max(0, min(img_width - text_width - padding, img_width - text_width)), max(0, min(padding, img_height - text_height))),  # top-right
                (max(0, min(padding, img_width - text_width)), max(0, min(img_height - text_height - padding, img_height - text_height))),  # bottom-left
                (max(0, min(img_width - text_width - padding, img_width - text_width)), max(0, min(img_height - text_height - padding, img_height - text_height))),  # bottom-right
            ]
            
            for pos in safe_positions_to_try:
                x, y = pos
                if (x >= 0 and y >= 0 and 
                    x + text_width <= img_width and 
                    y + text_height <= img_height):
                    positions.append(pos)
                    if len(positions) >= count:
                        break
        
        # Финальная проверка: фильтруем позиции, чтобы убедиться что все в пределах границ
        safe_positions = []
        for pos in positions:
            x, y = pos
            # Строгая проверка границ
            if (x >= 0 and 
                y >= 0 and 
                x + text_width <= img_width and 
                y + text_height <= img_height):
                safe_positions.append(pos)
        
        # Если все позиции отфильтровались, возвращаем хотя бы одну безопасную
        if not safe_positions:
            # Размещаем в левом верхнем углу с минимальным отступом
            safe_x = max(0, min(padding, img_width - text_width))
            safe_y = max(0, min(padding, img_height - text_height))
            safe_positions = [(safe_x, safe_y)]
        
        return safe_positions
    
    @staticmethod
    def _get_font(size: int) -> ImageFont.FreeTypeFont:
        """Получение шрифта"""
        font_paths = [
            "arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
        ]
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            except:
                continue
        
        return ImageFont.load_default()
    
    @staticmethod
    def _calculate_position(
        image_size: tuple,
        watermark_size: tuple,
        position: str
    ) -> tuple:
        """Вычисление позиции водяного знака"""
        img_width, img_height = image_size
        wm_width, wm_height = watermark_size
        
        if position == "center":
            return ((img_width - wm_width) // 2, (img_height - wm_height) // 2)
        elif position == "top-left":
            return (10, 10)
        elif position == "top-right":
            return (img_width - wm_width - 10, 10)
        elif position == "bottom-left":
            return (10, img_height - wm_height - 10)
        elif position == "bottom-right":
            return (img_width - wm_width - 10, img_height - wm_height - 10)
        else:
            return ((img_width - wm_width) // 2, (img_height - wm_height) // 2)
    
    @staticmethod
    def _calculate_text_position(
        image_size: tuple,
        text_size: tuple,
        position: str
    ) -> tuple:
        """Вычисление позиции текста с проверкой границ"""
        img_width, img_height = image_size
        text_width, text_height = text_size
        
        padding = 10
        
        if position == "center":
            x = max(0, min((img_width - text_width) // 2, img_width - text_width))
            y = max(0, min((img_height - text_height) // 2, img_height - text_height))
            return (x, y)
        elif position == "top-left":
            x = max(0, min(padding, img_width - text_width))
            y = max(0, min(padding, img_height - text_height))
            return (x, y)
        elif position == "top-right":
            x = max(0, min(img_width - text_width - padding, img_width - text_width))
            y = max(0, min(padding, img_height - text_height))
            return (x, y)
        elif position == "bottom-left":
            x = max(0, min(padding, img_width - text_width))
            y = max(0, min(img_height - text_height - padding, img_height - text_height))
            return (x, y)
        elif position == "bottom-right":
            x = max(0, min(img_width - text_width - padding, img_width - text_width))
            y = max(0, min(img_height - text_height - padding, img_height - text_height))
            return (x, y)
        else:
            # По умолчанию центр с проверкой границ
            x = max(0, min((img_width - text_width) // 2, img_width - text_width))
            y = max(0, min((img_height - text_height) // 2, img_height - text_height))
            return (x, y)
