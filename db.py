import os
import asyncpg
from datetime import date
from typing import List, Tuple, Optional

_pool: Optional[asyncpg.Pool] = None

async def init_db_pool(dsn: str):
    """Создаёт пул соединений к PostgreSQL и создаёт таблицу, если её нет."""
    global _pool
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10)
    async with _pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS birthdays (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                date TEXT NOT NULL
            )
        ''')

async def close_db_pool():
    """Закрывает пул соединений."""
    if _pool:
        await _pool.close()

def _get_connection():
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db_pool() first.")
    return _pool.acquire()

async def add_birthday(user_id: int, name: str, date_str: str):
    async with _get_connection() as conn:
        await conn.execute(
            "INSERT INTO birthdays (user_id, name, date) VALUES ($1, $2, $3)",
            user_id, name, date_str
        )

async def delete_birthday(user_id: int, name: str) -> int:
    async with _get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM birthdays WHERE user_id = $1 AND name = $2",
            user_id, name
        )
        return int(result.split()[-1])

async def get_birthdays(user_id: int) -> List[Tuple[str, str]]:
    async with _get_connection() as conn:
        rows = await conn.fetch(
            "SELECT name, date FROM birthdays WHERE user_id = $1 ORDER BY date",
            user_id
        )
        return [(row['name'], row['date']) for row in rows]

async def get_all_birthdays() -> List[Tuple[int, str, str]]:
    async with _get_connection() as conn:
        rows = await conn.fetch("SELECT user_id, name, date FROM birthdays")
        return [(row['user_id'], row['name'], row['date']) for row in rows]

async def exists_name(user_id: int, name: str) -> bool:
    async with _get_connection() as conn:
        row = await conn.fetchval(
            "SELECT 1 FROM birthdays WHERE user_id = $1 AND name = $2",
            user_id, name
        )
        return row is not None

async def update_birthday_date(user_id: int, name: str, new_date_str: str) -> bool:
    async with _get_connection() as conn:
        result = await conn.execute(
            "UPDATE birthdays SET date = $1 WHERE user_id = $2 AND name = $3",
            new_date_str, user_id, name
        )
        return int(result.split()[-1]) > 0
