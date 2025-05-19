from database.db import get_pending_verifications_count, get_pending_requisites_count_manual
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_operator_menu(counts: dict) -> ReplyKeyboardMarkup:
    requisites_count = get_pending_requisites_count_manual()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row(
        KeyboardButton(f"📄 Проверить документы ({counts['docs']})"),
        KeyboardButton(f"💳 Выдать реквизиты ({requisites_count})"),
    )
    kb.row(
        KeyboardButton(f"💰 Проверить оплату ({counts['payments']})"),
        KeyboardButton(f"🎥 Проверить видео ({counts['videos']})"),
    )
    kb.row(KeyboardButton("📋 Список заявок")
    )
    kb.row(KeyboardButton("📢 Рассылка")
    )

    return kb
