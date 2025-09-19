# create_user_universal.py
from init_db import SessionLocal, User
from passlib.hash import bcrypt

# --- Подключаемся к базе ---
session = SessionLocal()

# --- Определяем роль пользователя ---
user_type = input("Создать пользователя (admin/teacher/student): ").strip().lower()
if user_type not in ("admin", "teacher", "student"):
    print("Неверная роль пользователя")
    exit()

# --- Общие данные ---
login = input("Логин: ").strip()
password = input("Пароль: ").strip()
role = user_type

# --- Создаём объект пользователя в зависимости от роли ---
if user_type == "student":
    name_tuter = input("Имя пользователя: ").strip()
    new_user = User(
        login=login,
        password_hash=bcrypt.hash(password),
        role=role,
        name_tuter=name_tuter
    )
elif user_type == "teacher":
    name_tuter = input("Имя пользователя: ").strip()
    is_junior = int(input("is_junior (0/1): ").strip())
    is_senior = int(input("is_senior (0/1): ").strip())
    new_user = User(
        login=login,
        password_hash=bcrypt.hash(password),
        role=role,
        name_tuter=name_tuter,
        is_junior=is_junior,
        is_senior=is_senior
    )
else:  # admin
    new_user = User(
        login=login,
        password_hash=bcrypt.hash(password),
        role='admin',
        name_tuter='Admin',  # нужно заполнить, иначе NOT NULL ошибка
    )

# --- Сохраняем в БД ---
session.add(new_user)
session.commit()
session.close()

print(f"Пользователь {login} ({role}) создан")
