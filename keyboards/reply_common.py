from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

cancel_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("❌ Отмена")
)
