from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    bot_token: str
    active_model: str = "gpt-3.5-turbo" # Default model, easily switchable to "gemini/gemini-pro" or "claude-3-opus-20240229"
    
    # API keys for different providers
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    anthropic_api_key: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
