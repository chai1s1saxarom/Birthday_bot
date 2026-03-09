import os
import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime

from fastapi import FastAPI, Request
from aiogram.types import Update

from bot import bot, dp, days_until_next_birthday, format_date
from config import REMINDER_DAYS_BEFORE
import db

# --- Настройка вебхука для Render ---
BASE_URL = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:8000')
WEBHOOK_PATH = f"/webhook/{os.urandom(16).hex()}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# --- Фоновая задача напоминаний ---
async def reminder_worker():
    while True:
        today = date.today()
        all_rows = await db.get_all_birthdays()
        for user_id, name, date_str in all_rows:
            bd_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            days_left = days_until_next_birthday(bd_date, today)
            if days_left == REMINDER_DAYS_BEFORE:
                text = (f"Через {REMINDER_DAYS_BEFORE} дня будет день рождения у {name} "
                        f"({format_date(bd_date)}). Не забудьте поздравить!")
                try:
                    await bot.send_message(chat_id=user_id, text=text)
                except Exception:
                    # Логирование можно добавить
                    pass
        await asyncio.sleep(24 * 60 * 60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте: инициализируем пул БД
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL не задан!")
    await db.init_db_pool(database_url)

    # Устанавливаем вебхук
    await bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=dp.resolve_used_update_types()
    )
    # Запускаем фоновую задачу
    asyncio.create_task(reminder_worker())
    yield
    # При остановке: удаляем вебхук, закрываем пул и сессию бота
    await bot.delete_webhook()
    await bot.session.close()
    await db.close_db_pool()

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def webhook(request: Request) -> dict:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Bot is running"}