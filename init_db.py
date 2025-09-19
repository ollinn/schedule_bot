import uuid
from sqlalchemy import create_engine, Column, String, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.hash import bcrypt
import os
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/schedule_bot.db")
Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)


# Таблица пользователей
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    login = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "admin", "teacher", "student"
    name_tuter = Column(String, nullable=False)  # ФИО или имя
    telegram_id = Column(String, unique=True)
    is_junior = Column(Boolean, default=False)  
    is_senior = Column(Boolean, default=False)



# Таблица расписания
class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    time_start = Column(String, nullable=False)
    time_end = Column(String, nullable=True)
    cabinet = Column(String, nullable=True)
    teacher = Column(String, nullable=True)
    class_name = Column(String, nullable=True)
    weekday = Column(Enum("ПН", "ВТ", "СР", "ЧТ", "ПТ", name="weekday_enum"), nullable=False)
    subject = Column(String, nullable=True) 
      
class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    telegram_id = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


def init_db():
    Base.metadata.drop_all(bind=engine)   # <--- удаляем старые таблицы
    Base.metadata.create_all(bind=engine) # <--- создаём заново
    print("База пересоздана")

if __name__ == "__main__":
    init_db()