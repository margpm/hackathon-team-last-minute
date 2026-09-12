import logging
from atproto import AsyncClient
from app.config import settings

logger = logging.getLogger(__name__)

async def publish_to_bluesky(text: str) -> str:
    """
    Publish a post to Bluesky using the configured handle and app password.
    Returns the URI of the published post.
    """
    if not settings.bluesky_handle or not settings.bluesky_app_password:
        raise ValueError("Bluesky handle or app password not configured.")

    logger.info(f"Authenticating to Bluesky as {settings.bluesky_handle}...")
    client = AsyncClient()
    
    try:
        await client.login(settings.bluesky_handle, settings.bluesky_app_password)
        logger.debug("Successfully authenticated to Bluesky.")
        
        post = await client.send_post(text)
        logger.info(f"Successfully published to Bluesky! URI: {post.uri}")
        return post.uri
    except Exception as e:
        logger.error(f"Failed to publish to Bluesky: {e}", exc_info=True)
        raise e
