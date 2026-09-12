import aiosqlite
import logging

DB_PATH = "data/app.db"

async def init_db():
    """Create the necessary tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS meta_tokens (
                threads_user_id TEXT PRIMARY KEY,
                long_lived_token TEXT NOT NULL,
                telegram_user_id TEXT,
                expires_at INTEGER
            )
        ''')
        await db.commit()
    logging.info("Database initialized.")

async def save_token(threads_user_id: str, long_lived_token: str, telegram_user_id: str = None, expires_in: int = 0):
    """Save or update a Meta Threads token."""
    import time
    expires_at = int(time.time()) + expires_in if expires_in else 0
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO meta_tokens (threads_user_id, long_lived_token, telegram_user_id, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(threads_user_id) DO UPDATE SET
                long_lived_token = excluded.long_lived_token,
                telegram_user_id = COALESCE(excluded.telegram_user_id, meta_tokens.telegram_user_id),
                expires_at = excluded.expires_at
        ''', (threads_user_id, long_lived_token, telegram_user_id, expires_at))
        await db.commit()
    logging.info(f"Saved long-lived token for Threads user: {threads_user_id}")

async def get_token_by_telegram_id(telegram_user_id: str):
    """Retrieve a token using the Telegram User ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT long_lived_token, threads_user_id FROM meta_tokens WHERE telegram_user_id = ?', (telegram_user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"long_lived_token": row[0], "threads_user_id": row[1]}
            return None

async def get_all_tokens():
    """Retrieve all tokens (useful for startup)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT threads_user_id, long_lived_token, telegram_user_id FROM meta_tokens') as cursor:
            rows = await cursor.fetchall()
            return rows
