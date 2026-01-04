"""
Инициализация базы данных
"""
from app.models.database import init_db, engine, Base

if __name__ == "__main__":
    print("Инициализация базы данных...")
    init_db()
    print("База данных инициализирована!")
