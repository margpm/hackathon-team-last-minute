import json
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from typing import Any


_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def _configured_secrets() -> list[str]:
    names = (
        "BOT_TOKEN",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "ANTHROPIC_API_KEY",
        "META_CLIENT_SECRET",
        "BLUESKY_APP_PASSWORD",
    )
    secrets = [os.environ.get(name) for name in names]
    try:
        from app.config import settings

        secrets.extend(
            (
                settings.bot_token,
                settings.openai_api_key,
                settings.gemini_api_key,
                settings.anthropic_api_key,
                settings.meta_client_secret,
                settings.bluesky_app_password,
            )
        )
    except (ImportError, AttributeError):
        pass
    return sorted(
        {secret for secret in secrets if secret and len(secret) >= 8},
        key=len,
        reverse=True,
    )


def _redact_secrets(value: str) -> str:
    for secret in _configured_secrets():
        value = value.replace(secret, "[REDACTED]")
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value


def log_event(
    target: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Write one complete, machine-readable application event."""
    serialized = json.dumps(
        {"event": event, **fields},
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    )
    target.log(level, _redact_secrets(serialized))


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
        "data/logs/app.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8",
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
