from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import aiohttp
import logging
from app.config import settings

web_app = FastAPI()

@web_app.get("/login", response_class=HTMLResponse)
async def login():
    """
    Redirects the user to the Meta Threads login page.
    """
    if not settings.meta_client_id:
        return "Meta client ID is not configured."
        
    meta_oauth_url = (
        f"https://threads.net/oauth/authorize"
        f"?client_id={settings.meta_client_id}"
        f"&redirect_uri={settings.meta_redirect_uri}"
        f"&scope=threads_basic,threads_content_publish"
        f"&response_type=code"
    )
    return f'<a href="{meta_oauth_url}">Login with Meta Threads</a>'

@web_app.get("/callback")
async def callback(code: str = None, error: str = None, error_description: str = None):
    """
    The redirect link handler for Meta Threads OAuth.
    Extracts the authorization code and exchanges it for an access token.
    """
    if error:
        logging.error(f"Meta OAuth Error: {error} - {error_description}")
        return {"status": "error", "message": error_description}
        
    if not code:
        return {"status": "error", "message": "No authorization code provided."}
        
    logging.info("Received Meta authorization code. Exchanging for token...")
    
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
                
                # TODO: Store the long_lived_token, expires_in, and user_id in your database securely!
                # Link it with the corresponding Telegram user ID (which you'd pass via the OAuth 'state' param)
                logging.info(f"Successfully authenticated and retrieved long-lived token for Threads user: {user_id}")
                
                return {
                    "status": "success", 
                    "message": "Successfully authenticated with Threads and got long-lived token!",
                    "user_id": user_id,
                    "expires_in": expires_in
                    # Never return the actual token to the frontend in a real app
                }
