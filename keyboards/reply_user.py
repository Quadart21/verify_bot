from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_user_menu(is_verified: bool):
    if is_verified:
        return ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("💳 Запросить реквизиты")
        )
    else:
        return ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("✅ Пройти верификацию")
        )
