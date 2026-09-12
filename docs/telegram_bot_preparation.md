# Preparation Guide: Setting Up a Telegram Bot in Python

Before we write any Python code for our Telegram bot, we need to do a little bit of setup on Telegram itself and prepare our coding environment. Follow these steps to get everything ready!

---

## Step 1: Create the Bot on Telegram (BotFather)

Telegram has a special, official bot named **BotFather** that rules all other bots. We need to talk to him to create our bot and get our secret "keys".

1. Open the Telegram app on your phone or computer.
2. Search for `@BotFather` in the search bar and open the chat (make sure it has the blue verified checkmark).
3. Click **Start** or type `/start`.
4. Send the command `/newbot` to create a new bot.
5. BotFather will ask for two things:
   * **Name:** A display name for your bot (e.g., `Hackathon Helper`).
   * **Username:** A unique username that *must* end in `bot` (e.g., `MyAwesomeHackathon_bot`).
6. **Save your API Token:** If successful, BotFather will send you a message with an HTTP API Token. It looks like a long string of random characters (e.g., `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`). 
   * ⚠️ **IMPORTANT:** Treat this token like a password! Anyone who has it can control your bot. **Never share it or post it publicly.**

## Step 2: Prepare the Python Project

Now we need to set up the Python environment where our bot's code will live. 

1. Open a terminal (Mac/Linux) or Command Prompt/PowerShell (Windows).
2. Navigate to your project folder:
   ```bash
   cd path/to/your/project
   ```

### (Optional but highly recommended) Create a Virtual Environment
This keeps your bot's Python packages separate from the rest of your computer.
```bash
# Create the virtual environment
python3 -m venv venv

# Activate it (Mac/Linux)
source venv/bin/activate

# Activate it (Windows)
venv\Scripts\activate
```

## Step 3: Install the Required Libraries

We need a library to help Python communicate with Telegram. For beginners, `python-telegram-bot` is a fantastic and very popular choice. 

We also need `python-dotenv` to safely load our secret token.

Run this command in your terminal to install both:
```bash
pip install python-telegram-bot python-dotenv
```

## Step 4: Securely Store Your Token (.env File)

Remember that secret API token from Step 1? We need to give it to Python, but we *don't* want to write it directly in our code (otherwise, it might accidentally get uploaded to GitHub!).

1. In your project folder, create a new file named exactly `.env` (don't forget the dot!).
2. Open `.env` in your code editor and add your token like this:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ```
3. Save the file.
4. **Important:** Make sure `.env` is listed in your `.gitignore` file so it never gets uploaded to the internet! (If you look in the `.gitignore` of this project, you'll see `.env` is already ignored).

---

**You are now fully prepared!** Your bot is registered on Telegram, your Python environment is ready, and your secret token is safely stored. We can now start writing the Python code to make the bot come alive.
