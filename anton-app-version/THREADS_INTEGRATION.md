# Meta Threads API Integration Guide

This guide is intended for the VPS Coding Agent to help the user set up and test the Meta Threads integration.

## 1. Setup the Meta App (User Action)
1. Go to the [Meta App Dashboard](https://developers.facebook.com/apps/).
2. Create a new App (type: **None** or **Consumer**).
3. Add the **Threads API** product to the app.
4. Retrieve the **App ID** (`META_CLIENT_ID`) and **App Secret** (`META_CLIENT_SECRET`).
5. Configure the **OAuth Redirect URI** in the Threads API settings to match your VPS endpoint:
   `https://<YOUR_VPS_IP>:8000/callback` (or your domain).
6. Fill these values into the `.env` file on the VPS.

## 2. Walkthrough: The Authentication Flow
To authenticate a Telegram user and store their Threads access token:

1. Send the user to the login endpoint on the VPS, passing their Telegram ID as the state:
   `https://<YOUR_VPS_IP>:8000/login?telegram_id=<TELEGRAM_ID>`
2. The user will be redirected to Meta, asked to authorize, and then redirected back to the `/callback` endpoint.
3. The application will automatically:
   - Exchange the short-lived `code` for a short-lived `access_token`.
   - Exchange the short-lived token for a **Long-Lived Token** (60 days).
   - Save the `long_lived_token`, `threads_user_id`, and `telegram_user_id` into the SQLite database (`data/app.db`).

## 3. How to Verify the Token (Agent Action)
Once the user has completed the login flow, the coding agent can verify it by checking the SQLite database on the VPS:

```bash
# Run this inside the VPS to verify the token was stored:
sqlite3 anton-app-version/data/app.db "SELECT telegram_user_id, threads_user_id FROM meta_tokens;"
```

## 4. How to Make a Test Post to Threads (Agent Action)
Once the token is in the database, the agent can write a quick test script to verify publishing works. 
Publishing is a two-step process:

**Step A: Create a Media Container**
```python
import aiohttp
import asyncio

async def test_publish(access_token, threads_user_id, text="Hello Threads API! 🤖"):
    async with aiohttp.ClientSession() as session:
        # Step 1: Create container
        create_url = f"https://graph.threads.net/v1.0/{threads_user_id}/threads"
        async with session.post(create_url, data={
            "media_type": "TEXT",
            "text": text,
            "access_token": access_token
        }) as res:
            data = await res.json()
            creation_id = data.get("id")
            print(f"Container created: {creation_id}")
            
        # Step 2: Publish container
        publish_url = f"https://graph.threads.net/v1.0/{threads_user_id}/threads_publish"
        async with session.post(publish_url, data={
            "creation_id": creation_id,
            "access_token": access_token
        }) as res:
            data = await res.json()
            print(f"Post published! ID: {data.get('id')}")

# Usage (extract token from DB first)
# asyncio.run(test_publish("LONG_LIVED_TOKEN", "THREADS_USER_ID"))
```

## 5. Next Steps for the Agent
1. Help the user complete the Meta App setup and update the `.env` file.
2. Ask the user to click the `/login` link and authorize.
3. Verify the token was stored in `data/app.db`.
4. Integrate the `test_publish` logic into `app/bot.py` or `app/llm_client.py` as an LLM Tool/Function so the AI can post on the user's behalf!
