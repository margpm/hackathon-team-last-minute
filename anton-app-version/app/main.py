import uvicorn
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from app.logger import setup_logging

logger = logging.getLogger(__name__)

# Setup logging immediately
setup_logging()

from app.bot import start_bot
from app.config import settings
from app.web import web_app
from app.database import init_db, get_all_tokens

@asynccontextmanager
async def lifespan(app):
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Initialize the database and re-pick up tokens
    await init_db()
    tokens = await get_all_tokens()
    logger.info(f"Loaded {len(tokens)} long-lived Meta tokens from database.")
    
    task = None
    if settings.bot_token:
        logger.info("Starting ContextProof Telegram bot...")
        task = asyncio.create_task(start_bot())
    else:
        logger.warning("BOT_TOKEN is not configured; Telegram polling is disabled.")
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

web_app.router.lifespan_context = lifespan

if __name__ == "__main__":
    ssl_keyfile = "certs/key.pem"
    ssl_certfile = "certs/cert.pem"
    ssl_options = {}
    if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
        ssl_options = {"ssl_keyfile": ssl_keyfile, "ssl_certfile": ssl_certfile}
        logger.info("Starting HTTPS with the configured certificate files.")
    else:
        logger.warning("No certificate files found; starting HTTP for local/runtime health.")

    uvicorn.run(
        "app.main:web_app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
        **ssl_options,
    )
