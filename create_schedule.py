import os
import pandas as pd
from sqlalchemy import create_engine, Column, String, Time
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
import uuid

# --- Настройка базы данных ---
Base = declarative_base()
DB_FILE = "schedule.db"
engine = create_engine(f"sqlite:///{DB_FILE}", echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# --- Модель таблицы ---
class Schedule(Base):
    __tablename__ = 'schedules'
    id = Column(String, primary_key=True)
    time_start = Column(Time)
    time_end = Column(Time)
    cabinet = Column(String)
    teacher = Column(String)
    class_name = Column(String)
    weekday = Column(String)
    subject = Column(String)

# --- Создание таблицы если нет ---
Base.metadata.create_all(engine)

# --- Очистка таблицы ---
def clear_table():
    session.query(Schedule).delete()
    session.commit()
    print("Таблица schedules очищена")

# --- Путь к файлу Excel ---
file_path = os.path.join(os.path.dirname(__file__), "uploads", "schedule.xlsx")

# --- Загрузка расписания ---
def upload_schedule(file_path):
    df = pd.read_excel(file_path)

    # Преобразуем только если не datetime.time
    df['time_start'] = df['time_start'].apply(lambda x: x if isinstance(x, datetime.time) else pd.to_datetime(x).time())
    df['time_end'] = df['time_end'].apply(lambda x: x if isinstance(x, datetime.time) else pd.to_datetime(x).time())

    for _, row in df.iterrows():
        schedule = Schedule(
        id=str(uuid.uuid4()),  # генерируем уникальный id
        time_start=row['time_start'],
        time_end=row['time_end'],
        cabinet=row['cabinet'],
        teacher=row['teacher'],
        class_name=row['class_name'],
        weekday=row['weekday'],
        subject=row['subject']
    )
        session.add(schedule)
    session.commit()
    print("Расписание загружено")

# --- Основной запуск ---
if __name__ == "__main__":
    clear_table()
    upload_schedule(file_path)
