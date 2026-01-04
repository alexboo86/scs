"""
API роутеры
"""
from fastapi import APIRouter
from app.api import documents, users, admin

router = APIRouter()

router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(users.router, prefix="/users", tags=["users"])
# viewer роутер подключен напрямую в main.py для гибкости
router.include_router(admin.router, prefix="/admin", tags=["admin"])
