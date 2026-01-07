#!/usr/bin/env python3
"""
Скрипт для очистки старых записей из базы данных
Запуск: docker exec secure-content-backend python cleanup_old_sessions.py
"""
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, '/app')

from app.models.database import SessionLocal, ViewingSession
from datetime import datetime, timedelta

def main():
    print("=" * 60)
    print("  Database Cleanup - Old Viewing Sessions")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Проверяем текущее количество сессий
        total_count = db.query(ViewingSession).count()
        print(f"\n[INFO] Total viewing sessions: {total_count}")
        
        # Удаляем старые сессии (старше 7 дней)
        old_date = datetime.utcnow() - timedelta(days=7)
        old_sessions = db.query(ViewingSession).filter(
            ViewingSession.created_at < old_date
        ).all()
        old_count = len(old_sessions)
        
        print(f"[INFO] Old sessions (>7 days): {old_count}")
        
        if old_count > 0:
            deleted_count = db.query(ViewingSession).filter(
                ViewingSession.created_at < old_date
            ).delete()
            db.commit()
            print(f"[INFO] Deleted {deleted_count} old sessions")
        else:
            print("[INFO] No old sessions to delete")
        
        # Проверяем количество после очистки
        remaining_count = db.query(ViewingSession).count()
        print(f"[INFO] Remaining sessions: {remaining_count}")
        
        # Оптимизируем базу данных (VACUUM)
        print("\n[INFO] Optimizing database (VACUUM)...")
        try:
            from app.models.database import engine
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("VACUUM"))
                conn.commit()
            print("[INFO] Database optimized successfully")
        except Exception as e:
            print(f"[WARN] Could not optimize database: {e}")
            print("[INFO] You may need to run VACUUM manually via sqlite3")
        
    except Exception as e:
        print(f"[ERROR] Failed to cleanup: {e}")
        db.rollback()
        return 1
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("  Cleanup complete!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
