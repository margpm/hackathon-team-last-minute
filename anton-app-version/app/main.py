import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from app.bot import start_bot
from app.web import web_app

@asynccontextmanager
async def lifespan(app):
    # Start the telegram bot in the background
    logging.info("Starting Telegram Bot...")
    task = asyncio.create_task(start_bot())
    yield
    # Cleanup on shutdown (cancel the bot task if needed)
    task.cancel()

web_app.router.lifespan_context = lifespan

if __name__ == "__main__":
    # Run the web server (which also starts the bot via lifespan)
    uvicorn.run("app.main:web_app", host="0.0.0.0", port=8000, reload=False)
