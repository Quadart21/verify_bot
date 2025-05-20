from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_user_menu(is_verified: bool):
    if is_verified:
        return ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("💳 Запросить реквизиты"),
            KeyboardButton("Написать в поддержку")
        )
    else:
        return ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("✅ Пройти верификацию"),
            KeyboardButton("Написать в поддержку")
        )

def get_retry_keyboard(text="🔁 Повторить шаг"):
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton(text),
        KeyboardButton("🏠 В начало")
    )