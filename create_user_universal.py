from init_db import SessionLocal, User
from passlib.hash import bcrypt
from sqlalchemy.exc import IntegrityError

session = SessionLocal()

user_type = input("Создать пользователя (admin/teacher/student): ").strip().lower()
if user_type not in ("admin", "teacher", "student"):
    print("Неверная роль пользователя")
    exit()

login = input("Логин: ").strip()
password = input("Пароль: ").strip()
role = user_type

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
    is_junior = input("is_junior (0/1): ").strip()
    is_senior = input("is_senior (0/1): ").strip()
    if is_junior not in ("0", "1") or is_senior not in ("0", "1"):
        print("Ошибка: введите 0 или 1 для is_junior и is_senior")
        exit()
    new_user = User(
        login=login,
        password_hash=bcrypt.hash(password),
        role=role,
        name_tuter=name_tuter,
        is_junior=int(is_junior),
        is_senior=int(is_senior)
    )
else:  # admin
    new_user = User(
        login=login,
        password_hash=bcrypt.hash(password),
        role='admin',
        name_tuter='Admin',
    )

try:
    session.add(new_user)
    session.commit()
    print(f"Пользователь {login} ({role}) создан")
except IntegrityError:
    session.rollback()
    print("Ошибка: такой логин уже существует")
finally:
    session.close()
