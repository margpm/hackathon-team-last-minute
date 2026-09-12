import asyncio
import logging
from app.bot import start_bot

if __name__ == "__main__":
    logging.info("Starting Telegram Bot...")
    asyncio.run(start_bot())
