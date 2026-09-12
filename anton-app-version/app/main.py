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
    import os
    
    ssl_keyfile = "certs/key.pem"
    ssl_certfile = "certs/cert.pem"
    
    if not os.path.exists(ssl_keyfile) or not os.path.exists(ssl_certfile):
        logging.error("SSL certificates not found! Please run deploy.sh to generate them.")
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
