import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    # We store logs inside the mounted data volume so they persist
    os.makedirs("data/logs", exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) # Allow all levels, handlers will filter
    
    # Format: 2026-09-12 12:00:00 - app.bot - INFO - Message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler: rotating files, max 10MB each, keep 5 backups
    file_handler = RotatingFileHandler(
        "data/logs/app.log", maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG) # File captures everything including DEBUG
    
    # Console handler: only output INFO and above to avoid terminal spam
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Clear any existing handlers (e.g. default uvicorn/fastapi handlers that might duplicate)
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Reduce noise from chatty external libraries
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info("Logging configured successfully.")
