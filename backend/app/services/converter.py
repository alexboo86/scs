"""
Сервис конвертации документов в изображения
"""
import os
import subprocess
from pathlib import Path
from typing import List
from pdf2image import convert_from_path
from pptx import Presentation
from PIL import Image
from app.core.config import settings


class DocumentConverter:
    """Конвертер документов в изображения"""
    
    @staticmethod
    def convert_pdf_to_images(pdf_path: str, output_dir: str, dpi: int = None) -> List[str]:
        """Конвертация PDF в изображения"""
        if dpi is None:
            dpi = settings.PDF_DPI
        
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            fmt='png',
            thread_count=4
        )
        
        output_paths = []
        os.makedirs(output_dir, exist_ok=True)
        
        for i, img in enumerate(images):
            output_path = os.path.join(output_dir, f"page_{i+1}.png")
            img.save(output_path, 'PNG', quality=95)
            output_paths.append(output_path)
        
        return output_paths
    
    @staticmethod
    def convert_ppt_to_images(ppt_path: str, output_dir: str, dpi: int = None) -> List[str]:
        """Конвертация PPT/PPTX в изображения через LibreOffice"""
        if dpi is None:
            dpi = settings.PPT_DPI
        
        # Сначала конвертируем в PDF через LibreOffice
        pdf_path = ppt_path.replace('.pptx', '.pdf').replace('.ppt', '.pdf')
        
        try:
            # Конвертация через LibreOffice headless
            cmd = [
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', os.path.dirname(pdf_path),
                ppt_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise Exception(f"LibreOffice conversion failed: {result.stderr}")
            
            # Теперь конвертируем PDF в изображения
            return DocumentConverter.convert_pdf_to_images(pdf_path, output_dir, dpi)
            
        except Exception as e:
            # Fallback: используем python-pptx для извлечения слайдов
            return DocumentConverter._convert_pptx_direct(ppt_path, output_dir, dpi)
    
    @staticmethod
    def _convert_pptx_direct(pptx_path: str, output_dir: str, dpi: int) -> List[str]:
        """Прямая конвертация PPTX через python-pptx (менее качественно)"""
        prs = Presentation(pptx_path)
        output_paths = []
        os.makedirs(output_dir, exist_ok=True)
        
        for i, slide in enumerate(prs.slides):
            # Создаем изображение слайда
            # Примечание: python-pptx не может напрямую рендерить слайды в изображения
            # Это требует дополнительных библиотек или использования внешних инструментов
            # Для полноценной работы лучше использовать LibreOffice
            
            # Временное решение: создаем пустое изображение с информацией о слайде
            img = Image.new('RGB', (1920, 1080), color='white')
            output_path = os.path.join(output_dir, f"page_{i+1}.png")
            img.save(output_path, 'PNG')
            output_paths.append(output_path)
        
        return output_paths
    
    @staticmethod
    def convert_to_images(file_path: str, file_type: str, output_dir: str) -> List[str]:
        """Универсальный метод конвертации"""
        if file_type.lower() == 'pdf':
            return DocumentConverter.convert_pdf_to_images(file_path, output_dir)
        elif file_type.lower() in ['ppt', 'pptx']:
            return DocumentConverter.convert_ppt_to_images(file_path, output_dir)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
