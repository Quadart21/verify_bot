from aiogram import Bot, types
from config import GROUP_CHAT_ID

async def notify_group(bot: Bot, text: str, user_id: int = None, section: str = None):
    try:
        if user_id and section:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    text="📂 Открыть заявку",
                    url=f"https://t.me/{(await bot.me).username}?start={user_id}_{section}"
                )
            )
            await bot.send_message(GROUP_CHAT_ID, text, reply_markup=keyboard)
        else:
            await bot.send_message(GROUP_CHAT_ID, text)
    except Exception as e:
        print(f"[ERROR] Failed to send group notification: {e}")
