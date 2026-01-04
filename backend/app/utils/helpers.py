"""
Вспомогательные функции
"""
import hashlib
import re
from pathlib import Path


def secure_filename(filename: str) -> str:
    """Безопасное имя файла"""
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('-')


def calculate_file_hash(file_path: str) -> str:
    """Вычисление хеша файла"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
