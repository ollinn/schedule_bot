from init_db import SessionLocal, User
from passlib.hash import bcrypt

# Создаём сессию для работы с БД
session = SessionLocal()

# --- Параметры нового пользователя ---
login = "SofiyaATeacher"          # логин пользователя
password = "5BJZT6"        # пароль в открытом виде (для теста)
role = "teacher"            # роли: admin / teacher / student
name_tuter = "Соня А"  # имя пользователя
#is_junior = 1
is_senior = 1
# --- Создаём объект пользователя с хешем пароля ---
new_user = User(
    login=login,
    password_hash=bcrypt.hash(password),
    role=role,
    name_tuter=name_tuter,
    #is_junior = is_junior,
    is_senior = is_senior
)

# --- Добавляем в БД ---
session.add(new_user)
session.commit()
session.close()

print(f"Пользователь {login} ({role}) создан")