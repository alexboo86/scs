"""
Модели базы данных
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    document_accesses = relationship("DocumentAccess", back_populates="user")
    viewing_sessions = relationship("ViewingSession", back_populates="user")


class Document(Base):
    """Модель документа"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, unique=True, index=True)
    file_type = Column(String, nullable=False)  # pdf, ppt, pptx
    total_pages = Column(Integer, nullable=False)
    access_token = Column(String, unique=True, index=True, nullable=False)
    watermark_settings = Column(Text, nullable=True)  # JSON строка
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True)
    
    # Связи
    accesses = relationship("DocumentAccess", back_populates="document")
    viewing_sessions = relationship("ViewingSession", back_populates="document")


class DocumentAccess(Base):
    """Доступ пользователя к документу"""
    __tablename__ = "document_accesses"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(String, nullable=True)
    
    # Связи
    document = relationship("Document", back_populates="accesses")
    user = relationship("User", back_populates="document_accesses")


class ViewingSession(Base):
    """Сессия просмотра документа"""
    __tablename__ = "viewing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Опционально - упрощенная версия
    session_token = Column(String, unique=True, index=True, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_access = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    document = relationship("Document", back_populates="viewing_sessions")
    user = relationship("User", back_populates="viewing_sessions")


class StaticWatermark(Base):
    """Статический водяной знак (логотип школы)"""
    __tablename__ = "static_watermarks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    position = Column(String, default="center")  # center, top-left, top-right, etc.
    opacity = Column(Float, default=0.3)
    scale = Column(Float, default=0.2)  # Размер относительно страницы
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GlobalWatermarkSettings(Base):
    """Глобальные настройки водяных знаков (для всех документов)"""
    __tablename__ = "global_watermark_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    settings_json = Column(Text, nullable=False)  # JSON строка с настройками
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdminUser(Base):
    """Модель администратора"""
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(bind=engine)
    
    # Создаем дефолтного админа если его нет
    from app.core.security import get_password_hash
    db = SessionLocal()
    try:
        admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if not admin:
            default_password = get_password_hash("admin123")  # Измените пароль!
            admin = AdminUser(
                username="admin",
                hashed_password=default_password,
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("⚠️  Создан дефолтный админ: username=admin, password=admin123")
            print("⚠️  ВАЖНО: Измените пароль после первого входа!")
    except Exception as e:
        print(f"Ошибка создания дефолтного админа: {e}")
    finally:
        db.close()


def get_db():
    """Получение сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
