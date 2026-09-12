from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import aiohttp
import logging
from app.config import settings
from app.database import save_token

web_app = FastAPI()

@web_app.get("/login", response_class=HTMLResponse)
async def login(telegram_id: str = "unknown"):
    """
    Redirects the user to the Meta Threads login page.
    Pass telegram_id as a query param (e.g. /login?telegram_id=12345) to link accounts.
    """
    if not settings.meta_client_id:
        return "Meta client ID is not configured."
        
    meta_oauth_url = (
        f"https://threads.net/oauth/authorize"
        f"?client_id={settings.meta_client_id}"
        f"&redirect_uri={settings.meta_redirect_uri}"
        f"&scope=threads_basic,threads_content_publish"
        f"&response_type=code"
        f"&state={telegram_id}"
    )
    return f'<a href="{meta_oauth_url}">Login with Meta Threads</a>'

@web_app.get("/callback")
async def callback(code: str = None, state: str = None, error: str = None, error_description: str = None):
    """
    The redirect link handler for Meta Threads OAuth.
    Extracts the authorization code and exchanges it for an access token.
    """
    if error:
        logging.error(f"Meta OAuth Error: {error} - {error_description}")
        return {"status": "error", "message": error_description}
        
    if not code:
        return {"status": "error", "message": "No authorization code provided."}
        
    logging.info(f"Received Meta authorization code (state/telegram_id: {state}). Exchanging for token...")
    
    # Exchange the code for an access token
    token_url = "https://graph.threads.net/oauth/access_token"
    payload = {
        "client_id": settings.meta_client_id,
        "client_secret": settings.meta_client_secret,
        "grant_type": "authorization_code",
        "redirect_uri": settings.meta_redirect_uri,
        "code": code
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=payload) as response:
            data = await response.json()
            if response.status != 200:
                logging.error(f"Failed to get token: {data}")
                return {"status": "error", "message": "Failed to exchange code for token.", "details": data}
                
            short_lived_token = data.get("access_token")
            user_id = data.get("user_id")
            
            if not short_lived_token:
                return {"status": "error", "message": "No access token in response"}
                
            logging.info(f"Got short-lived token for user {user_id}. Exchanging for long-lived token...")
            
            # Exchange for long-lived token
            long_lived_url = (
                f"https://graph.threads.net/access_token"
                f"?grant_type=th_exchange_token"
                f"&client_secret={settings.meta_client_secret}"
                f"&access_token={short_lived_token}"
            )
            
            async with session.get(long_lived_url) as ll_response:
                ll_data = await ll_response.json()
                if ll_response.status != 200:
                    logging.error(f"Failed to get long-lived token: {ll_data}")
                    return {"status": "error", "message": "Failed to exchange for long-lived token.", "details": ll_data}
                
                long_lived_token = ll_data.get("access_token")
                expires_in = ll_data.get("expires_in") # Typically 60 days in seconds
                
                # Store the long_lived_token in the SQLite database
                await save_token(
                    threads_user_id=str(user_id),
                    long_lived_token=long_lived_token,
                    telegram_user_id=state,
                    expires_in=expires_in
                )
                
                logging.info(f"Successfully authenticated and saved long-lived token for Threads user: {user_id}")
                
                return {
                    "status": "success", 
                    "message": "Successfully authenticated with Threads and saved token!",
                    "threads_user_id": user_id,
                    "telegram_user_id": state
                }
