import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from app.config import settings
from app.llm_client import generate_response

logger = logging.getLogger(__name__)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! I am your AI assistant. Send me a message and I'll route it to the configured LLM.")

@dp.message()
async def handle_message(message: types.Message):
    # Telegram topic or thread id can be derived like this for proxying to threads:
    thread_id = str(message.message_thread_id) if message.message_thread_id else str(message.chat.id)
    
    logger.debug(f"Received message from user {message.from_user.id} in thread {thread_id}: {message.text}")
    
    loading_msg = await message.reply("Thinking...")
    try:
        reply_text = await generate_response(prompt=message.text, thread_id=thread_id)
        logger.debug(f"Generated response for thread {thread_id}: {reply_text[:50]}...")
        await loading_msg.edit_text(reply_text)
    except Exception as e:
        logger.error(f"Error generating response for thread {thread_id}: {e}", exc_info=True)
        await loading_msg.edit_text(f"Sorry, an error occurred: {str(e)}")

async def start_bot():
    await dp.start_polling(bot)
