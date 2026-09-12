from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str | None = None
    active_model: str = "gpt-4o-mini"
    
    # API keys for different providers
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    anthropic_api_key: str | None = None
    
    # Meta Threads API OAuth
    meta_client_id: str | None = None
    meta_client_secret: str | None = None
    meta_redirect_uri: str = "https://your-domain.com/callback"
    
    # Bluesky / AT Protocol API
    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None

    # Public Bluesky AppView; app.bsky.feed.searchPosts is an unauthenticated GET.
    bluesky_search_url: str = (
        "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
    )
    bluesky_result_limit: int = 30
    bluesky_timeout_seconds: float = 15.0
    bluesky_language: str = "en"

    app_host: str = "0.0.0.0"
    app_port: int = 8000


settings = Settings()
