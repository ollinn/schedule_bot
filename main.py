import os
import datetime
import pandas as pd
import uuid
from dotenv import load_dotenv
from passlib.hash import bcrypt
from sqlalchemy import asc
from telegram import ReplyKeyboardMarkup, Update
from datetime import timedelta

from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

from init_db import SessionLocal, User, Schedule, UserSession


# ===================== Утилиты для работы с пользователями =====================
def get_user_by_telegram(telegram_id: int):
    """Вернуть User по telegram_id (через таблицу user_sessions)."""
    s = SessionLocal()
    try:
        sess = s.query(UserSession).filter_by(telegram_id=str(telegram_id)).first()
        if not sess:
            return None
        user = s.query(User).filter_by(id=sess.user_id).first()
        return user
    finally:
        s.close()

def create_user_session(user_id: str, telegram_id: int):
    """Создаёт/обновляет сессию: один telegram_id => одна сессия.
       Возвращает True/False."""
    s = SessionLocal()
    try:
        # если этот telegram_id уже привязан к другому user — удалим старую запись
        s.query(UserSession).filter_by(telegram_id=str(telegram_id)).delete()
        us = UserSession(id=str(uuid.uuid4()), user_id=user_id, telegram_id=str(telegram_id))
        s.add(us)
        s.commit()
        return True
    except Exception as e:
        s.rollback()
        return False
    finally:
        s.close()


def clear_user_session(telegram_id: int):
    """Удаляет сессию по telegram_id. Возвращает True, если удалил."""
    s = SessionLocal()
    try:
        deleted = s.query(UserSession).filter_by(telegram_id=str(telegram_id)).delete()
        s.commit()
        return bool(deleted)
    finally:
        s.close()

def get_user_by_login(login: str):
    s = SessionLocal()
    try:
        return s.query(User).filter_by(login=login).first()
    finally:
        s.close()



def verify_password(user, password: str) -> bool:
    if not user:
        return False
    return bcrypt.verify(password, user.password_hash)


# ===================== Клавиатура =====================
MAIN_KEYBOARD = [
    ["ПН", "ВТ", "СР"],
    ["ЧТ", "ПТ", "На сегодня"],
    ["На завтра", "На неделю", "Выйти"]
]

def main_keyboard():
    return ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)


# ===================== Авторизация =====================
LOGIN, PASSWORD = range(2)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram(update.effective_user.id)
    if user:
        await update.message.reply_text(
            f"Вы уже авторизованы как {user.name_tuter} ({user.role})",
            reply_markup=main_keyboard()
        )
        return
    await update.message.reply_text("Привет. Чтобы продолжить, выполните /login")

async def cmd_login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите ваш логин:")
    return LOGIN

async def login_receive_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['login_try'] = update.message.text.strip()
    await update.message.reply_text("Введите пароль:")
    return PASSWORD

async def login_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    login = context.user_data.get('login_try')
    password = update.message.text.strip()
    user = get_user_by_login(login)
    if not user:
        await update.message.reply_text("Пользователь с таким логином не найден. Попробуйте /login заново.")
        return ConversationHandler.END
    if not verify_password(user, password):
        await update.message.reply_text("Неверный пароль.")
        return ConversationHandler.END

    # после успешной проверки пароля
    create_user_session(user.id, update.effective_user.id)
    await update.message.reply_text(
        f"Успешно! Вы вошли как {user.name_tuter} ({user.role}).",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END

async def cmd_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cleared = clear_user_session(update.effective_user.id)
    if cleared:
        await update.message.reply_text("Вы вышли. Для входа используйте /login")
    else:
        await update.message.reply_text("Вы не были привязаны к учётной записи.")

login_conv = ConversationHandler(
    entry_points=[CommandHandler('login', cmd_login_start)],
    states={
        LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_receive_login)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_receive_password)],
    },
    fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
)


# ===================== Работа с расписанием =====================
WEEK_MAP_NUM_TO_RU = {1: "ПН", 2: "ВТ", 3: "СР", 4: "ЧТ", 5: "ПТ"}

def ru_weekday_from_isoweekday(n: int):
    return WEEK_MAP_NUM_TO_RU.get(n)

def get_schedule_for_teacher(teacher_name: str, weekday_ru: str):
    s = SessionLocal()
    try:
        return s.query(Schedule).filter_by(weekday=weekday_ru, teacher=teacher_name).order_by(asc(Schedule.time_start)).all()
    finally:
        s.close()

def get_schedule_for_class(class_name: str, weekday_ru: str):
    s = SessionLocal()
    try:
        return s.query(Schedule).filter_by(weekday=weekday_ru, class_name=class_name).order_by(asc(Schedule.time_start)).all()
    finally:
        s.close()


def format_schedule_rows(rows, role):
    lines = []
    
    for i, r in enumerate(rows, start=1):
        ts = str(r.time_start or '')
        te = str(r.time_end or '')
        period = f"{ts}–{te}" if te else ts

        if role == 'student':
            parts = [f"{i}. <b>{period}</b> | {r.subject or ''}"]
            if r.teacher:
                parts.append(f"📚<b>Преподаватель:</b> {r.teacher}")
            if r.cabinet:
                parts.append(f"🏫<b>Кабинет:</b> {r.cabinet}")
        elif role == 'teacher':
            parts = [f"{i}. <b>{period}</b> | {r.subject or ''}"]
            if r.class_name:
                parts.append(f"🧒🏼<b>Класс:</b> {r.class_name}")
            if r.cabinet:
                parts.append(f"🏫<b>Кабинет:</b> {r.cabinet}")
        else:
            parts = [f"{i}. {period} | {r.subject or ''}"]

        lines.append("\n".join(parts))

    return "\n\n".join(lines) if lines else "Нет занятий на выбранный день."



def format_schedule_with_header(rows, role, date_obj):
    weekday_en = date_obj.strftime("%A")
    weekday_ru = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }[weekday_en]

    header = f"<b>{weekday_ru}. {date_obj.strftime('%d.%m')}</b>"
    schedule_text = format_schedule_rows(rows, role)

    return f"{header}\n{schedule_text}"

from datetime import datetime, timedelta

def format_schedule_rows(rows, role):
    lines = []
    
    for i, r in enumerate(rows, start=1):
        ts = str(r.time_start or '')
        te = str(r.time_end or '')
        period = f"{ts}–{te}" if te else ts

        if role == 'student':
            parts = [f"{i}. <b>{period}</b> | {r.subject or ''}"]
            if r.teacher:
                parts.append(f"📚<b>Преподаватель:</b> {r.teacher}")
            if r.cabinet:
                parts.append(f"🏫<b>Кабинет:</b> {r.cabinet}")
        elif role == 'teacher':
            parts = [f"{i}. <b>{period}</b> | {r.subject or ''}"]
            if r.class_name:
                parts.append(f"🧒🏼<b>Класс:</b> {r.class_name}")
            if r.cabinet:
                parts.append(f"🏫<b>Кабинет:</b> {r.cabinet}")
        else:
            parts = [f"{i}. {period} | {r.subject or ''}"]

        lines.append("\n".join(parts))

    return "\n\n".join(lines) if lines else "Нет занятий на выбранный день."


def format_schedule_with_header(rows, role, date_obj):
    weekday_en = date_obj.strftime("%A")
    weekday_ru = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }[weekday_en]

    header = f"<b>{weekday_ru}. {date_obj.strftime('%d.%m')}</b>"
    schedule_text = format_schedule_rows(rows, role)

    return f"{header}\n{schedule_text}"


async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    text = update.message.text.strip()
    user = get_user_by_telegram(update.effective_user.id)
    if not user:
        await update.message.reply_text("Сначала /login")
        return

    # Сегодня
    if text == "На сегодня":
        date_obj = datetime.today().date()
        weekday_ru = ru_weekday_from_isoweekday(date_obj.isoweekday())
        if not weekday_ru:
            await update.message.reply_text("Сегодня выходной.")
            return

    # Завтра
    elif text == "На завтра":
        date_obj = (datetime.today() + timedelta(days=1)).date()
        weekday_ru = ru_weekday_from_isoweekday(date_obj.isoweekday())
        if not weekday_ru:
            await update.message.reply_text("Завтра выходной.")
            return

    # Неделя
    elif text == "На неделю":
        for offset, d in enumerate(["ПН","ВТ","СР","ЧТ","ПТ"]):
            # определяем дату для каждого дня
            today = datetime.today()
            weekday_num = today.isoweekday()
            delta = offset - (weekday_num - 1)
            date_obj = (today + timedelta(days=delta)).date()

            if user.role == 'teacher':
                rows = get_schedule_for_teacher(user.name_tuter, d)
            else:
                rows = get_schedule_for_class(user.name_tuter, d)

            if rows:
                await update.message.reply_text(
                    text=format_schedule_with_header(rows, user.role, date_obj),
                    parse_mode="HTML"
                )
        return

    # Конкретный день (ПН–ПТ)
    elif text in ["ПН","ВТ","СР","ЧТ","ПТ"]:
        today = datetime.today()
        weekday_num = today.isoweekday()  # 1=ПН
        target_num = ["ПН","ВТ","СР","ЧТ","ПТ"].index(text) + 1
        delta = target_num - weekday_num
        date_obj = (today + timedelta(days=delta)).date()
        weekday_ru = text

    elif text == "Выйти":
        await cmd_logout(update, context)
        return
    else:
        await update.message.reply_text("Команда не распознана. Используйте кнопки.")
        return

    # Загружаем расписание
    if user.role == 'teacher':
        rows = get_schedule_for_teacher(user.name_tuter, weekday_ru)
    elif user.role == 'student':
        rows = get_schedule_for_class(user.name_tuter, weekday_ru)
    else:
        await update.message.reply_text("Команда доступна только учителям и ученикам.")
        return

    await update.message.reply_text(
        text=format_schedule_with_header(rows, user.role, date_obj),
        parse_mode="HTML"
    )



# ===================== Загрузка файла расписания (для админа) =====================
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

import uuid
import pandas as pd
from sqlalchemy.orm import Session


def normalize_class(value):
    """Нормализация значения класса"""
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        # Если это число, убираем .0
        return str(int(float(value)))
    except (ValueError, TypeError):
        # Если это строка (например, "11А")
        return str(value).strip()


def normalize_teacher(value):
    """Нормализация ФИО преподавателя"""
    if pd.isna(value) or str(value).strip() == "":
        return None  # допускаем пустого учителя
    return str(value).strip()


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_telegram(update.effective_user.id)
    if not user or user.role != 'admin':
        await update.message.reply_text("Доступ запрещён. Только администратор может загружать расписание.")
        return

    doc = update.message.document
    if not doc:
        await update.message.reply_text("Отправьте файл .xlsx")
        return
    if not (doc.file_name.endswith(".xlsx") or doc.file_name.endswith(".xls")):
        await update.message.reply_text("Нужен файл .xlsx")
        return

    local_path = os.path.join(UPLOADS_DIR, doc.file_name)
    file = await doc.get_file()
    await file.download_to_drive(custom_path=local_path)

    df = pd.read_excel(local_path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required_columns = {'subject', 'weekday', 'time_start', 'class_name'}
    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"В файле нет обязательных колонок: {required_columns - set(df.columns)}. "
            f"Найдены: {list(df.columns)}"
        )

    def normalize_class_name(val):
        """Нормализует значение класса: 9.0 -> '9', 10 -> '10', '9А' остаётся '9А'"""
        import math
        if pd.isna(val):
            return None
        if isinstance(val, int):
            return str(val)
        if isinstance(val, float):
            if math.isfinite(val) and val.is_integer():
                return str(int(val))
            return str(val).strip()
        s = str(val).strip()
        try:
            f = float(s.replace(',', '.'))
            if f.is_integer():
                return str(int(f))
        except Exception:
            pass
        return s

    import datetime as _dt

    def to_time(val):
        if pd.isna(val):
            return None
        if hasattr(val, 'time'):
            return val.time()
        if isinstance(val, _dt.time):
            return val
        try:
            return pd.to_datetime(val).time()
        except Exception:
            return None

    s = SessionLocal()
    try:
        # очищаем старое расписание
        s.query(Schedule).delete()
        s.commit()

        for _, row in df.iterrows():
            ts = to_time(row.get('time_start'))
            te = to_time(row.get('time_end')) if 'time_end' in df.columns else None
            class_name_normalized = normalize_class_name(row.get('class_name'))

            # обработка teacher
            teacher_value = row.get('teacher')
            teacher_value = None if pd.isna(teacher_value) else str(teacher_value).strip()

            teachers = []
            if teacher_value:
                tv = teacher_value.lower()
                if tv == "все":
                    teachers = s.query(User).filter(User.role == 'teacher').all()
                elif tv == "младшая школа":
                    teachers = s.query(User).filter(User.role == 'teacher', User.is_junior == True).all()
                elif tv == "старшая школа":
                    teachers = s.query(User).filter(User.role == 'teacher', User.is_senior == True).all()
                else:
                    t = s.query(User).filter(User.role == 'teacher', User.name_tuter == teacher_value).first()
                    teachers = [t] if t else []

            # если есть учителя → создаём записи для каждого
            if teachers:
                for t in teachers:
                    sch = Schedule(
                        id=str(uuid.uuid4()),
                        time_start=ts.strftime("%H:%M") if ts else None,
                        time_end=te.strftime("%H:%M") if te else None,
                        cabinet=None if pd.isna(row.get('cabinet')) else str(row.get('cabinet')).strip(),
                        teacher=t.name_tuter if t else None,
                        class_name=class_name_normalized,
                        weekday=str(row.get('weekday')).strip() if not pd.isna(row.get('weekday')) else None,
                        subject=str(row.get('subject')).strip() if not pd.isna(row.get('subject')) else None
                    )
                    s.add(sch)
            else:
                # даже если teacher нет или не найден → сохраняем строку без учителя
                sch = Schedule(
                    id=str(uuid.uuid4()),
                    time_start=ts.strftime("%H:%M") if ts else None,
                    time_end=te.strftime("%H:%M") if te else None,
                    cabinet=None if pd.isna(row.get('cabinet')) else str(row.get('cabinet')).strip(),
                    teacher=None,
                    class_name=class_name_normalized,
                    weekday=str(row.get('weekday')).strip() if not pd.isna(row.get('weekday')) else None,
                    subject=str(row.get('subject')).strip() if not pd.isna(row.get('subject')) else None
                )
                s.add(sch)

        s.commit()
        await update.message.reply_text("Расписание загружено и таблица обновлена.")
    except Exception as e:
        s.rollback()
        await update.message.reply_text(f"Ошибка при загрузке: {e}")
    finally:
        s.close()



# ===================== Запуск бота =====================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(login_conv)
app.add_handler(CommandHandler("logout", cmd_logout))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice))

print("Бот запущен")
app.run_polling()
