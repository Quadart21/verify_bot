from aiogram import Bot
from config import GROUP_CHAT_ID

async def notify_group(bot: Bot, text: str):
    try:
        await bot.send_message(GROUP_CHAT_ID, text)
    except Exception as e:
        print(f"[ERROR] Failed to send group notification: {e}")
