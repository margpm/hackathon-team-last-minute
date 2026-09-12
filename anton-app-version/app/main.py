import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from app.logger import setup_logging

logger = logging.getLogger(__name__)

# Setup logging immediately
setup_logging()

from app.bot import start_bot
from app.web import web_app
from app.database import init_db, get_all_tokens
import os

@asynccontextmanager
async def lifespan(app):
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Initialize the database and re-pick up tokens
    await init_db()
    tokens = await get_all_tokens()
    logger.info(f"Loaded {len(tokens)} long-lived Meta tokens from database.")
    
    # Start the telegram bot in the background
    logger.info("Starting Telegram Bot...")
    task = asyncio.create_task(start_bot())
    yield
    # Cleanup on shutdown (cancel the bot task if needed)
    task.cancel()

web_app.router.lifespan_context = lifespan

if __name__ == "__main__":
    import os
    
    ssl_keyfile = "certs/key.pem"
    ssl_certfile = "certs/cert.pem"
    
    if not os.path.exists(ssl_keyfile) or not os.path.exists(ssl_certfile):
        logger.error("SSL certificates not found! Please run deploy.sh to generate them.")
        exit(1)
        
    # Run the web server using HTTPS only
    uvicorn.run(
        "app.main:web_app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )
