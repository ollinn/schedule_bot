# migrate_add_user_sessions.py
import uuid
from init_db import engine, SessionLocal, User, UserSession
from sqlalchemy.exc import IntegrityError

def run_migration():
    # 1) Создать таблицу user_sessions, если её нет
    UserSession.__table__.create(bind=engine, checkfirst=True)
    print("Таблица user_sessions создана (если ещё не была).")

    s = SessionLocal()
    try:
        # 2) Перенести существующие telegram_id из users (если есть)
        users_with_telegram = s.query(User).filter(User.telegram_id != None).all()
        print(f"Найдено {len(users_with_telegram)} пользователей с telegram_id для миграции.")
        for u in users_with_telegram:
            tg = u.telegram_id
            if not tg:
                continue
            # если сессия с таким telegram_id уже есть — пропускаем
            exists = s.query(UserSession).filter_by(telegram_id=str(tg)).first()
            if exists:
                print(f"telegram_id {tg} уже мигрирован — пропуск.")
                # если нужно — можно обновить user_id, но пропустим
                continue
            us = UserSession(
                id=str(uuid.uuid4()),
                user_id=u.id,
                telegram_id=str(tg)
            )
            s.add(us)

            # опционально: очищаем поле users.telegram_id чтобы избежать дублирования
            u.telegram_id = None

        s.commit()
        print("Миграция завершена, данные перенесены и users.telegram_id очищены.")
    except Exception as e:
        s.rollback()
        print("Ошибка миграции:", e)
    finally:
        s.close()

if __name__ == "__main__":
    run_migration()
