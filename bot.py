import asyncio
from datetime import datetime, date, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

from config import BOT_TOKEN, REMINDER_DAYS_BEFORE
import db


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def parse_date(date_str: str) -> date | None:
    try:
        parsed = datetime.strptime(date_str, "%d.%m.%Y").date()
        if parsed > date.today():
            return None  
        return parsed
    except ValueError:
        return None



def format_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def days_until_next_birthday(bd: date, today: date) -> int:
    this_year = bd.replace(year=today.year)
    if this_year < today:
        this_year = this_year.replace(year=today.year + 1)
    return (this_year - today).days


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Привет! Я бот-напоминалка о днях рождения.\n\n"
        "Команды:\n"
        "/add Имя DD.MM.YYYY — добавить день рождения\n"
        "/delete Имя — удалить\n"
        "/list — список сохранённых\n"
        "/help — помощь"
    )
    await message.answer(text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "Команды:\n"
        "/add Имя DD.MM.YYYY — добавить\n"
        "/edit Имя DD.MM.YYYY — изменить дату\n"
        "/delete Имя — удалить\n"
        "/list — список\n\n"
        "Правила:\n"
        "• Имена уникальны для вас\n"
        "• Только прошлые даты рождения\n"
        "• Формат: DD.MM.YYYY"
    )
    await message.answer(text)


@dp.message(Command("add"))
async def cmd_add(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Формат: /add Имя DD.MM.YYYY")
        return

    name = args[1].strip()
    date_str = args[2].strip()

    if not name:
        await message.answer("Имя не должно быть пустым.")
        return

    if await db.exists_name(message.from_user.id, name):
        await message.answer(f"Запись с именем '{name}' уже существует. Используйте /edit.")
        return

    bd_date = parse_date(date_str)
    if not bd_date:
        await message.answer(
            "Неверный формат даты или дата в будущем.\n"
            "Используйте DD.MM.YYYY (прошлая дата)."
        )
        return

    await db.add_birthday(message.from_user.id, name, format_date(bd_date))
    await message.answer(f"Сохранил: {name} — {format_date(bd_date)}")


@dp.message(Command("delete"))
async def cmd_delete(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Формат: /delete Имя\nПример: /delete Иван")
        return

    name = args[1].strip()
    if not name:
        await message.answer("Имя не должно быть пустым.")
        return

    deleted = await db.delete_birthday(message.from_user.id, name)
    if deleted:
        await message.answer(f"Удалил запись для: {name}")
    else:
        await message.answer("Запись с таким именем не найдена.")


@dp.message(Command("edit"))
async def cmd_edit(message: Message):
    args = message.text.split(maxsplit=3)
    if len(args) < 3:
        await message.answer(
            "Формат: /edit Имя DD.MM.YYYY\n"
            "Пример: /edit Иван 15.06.1985"
        )
        return

    name = args[1].strip()
    new_date_str = args[2].strip()

    if not name:
        await message.answer("Имя не должно быть пустым.")
        return

    new_bd_date = parse_date(new_date_str)
    if not new_bd_date:
        await message.answer(
            "Неверный формат даты или дата в будущем.\n"
            "Используйте DD.MM.YYYY (прошлая дата)."
        )
        return

    if not await db.exists_name(message.from_user.id, name):
        await message.answer(f"Запись для '{name}' не найдена.")
        return

    success = await db.update_birthday_date(
        message.from_user.id, name, format_date(new_bd_date)
    )
    if success:
        await message.answer(f"Обновил день рождения: {name} — {format_date(new_bd_date)}")
    else:
        await message.answer("Ошибка при обновлении.")


@dp.message(Command("list"))
async def cmd_list(message: Message):
    rows = await db.get_birthdays(message.from_user.id)
    if not rows:
        await message.answer("У вас пока нет сохранённых дней рождения.")
        return

    today = date.today()
    lines = []
    for name, date_str in rows:
        bd_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        days_left = days_until_next_birthday(bd_date, today)
        lines.append(f"{name}: {date_str} (через {days_left} дн.)")

    await message.answer("Ваши дни рождения:\n" + "\n".join(lines))


# async def main():
#     await db.init_db()
#     asyncio.create_task(reminder_worker())
#     await dp.start_polling(bot)


# if __name__ == "__main__":
#     asyncio.run(main())
