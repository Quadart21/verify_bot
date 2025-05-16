from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_operator_menu(counts: dict = None, layout: list = None):
    counts = counts or {"docs": 0, "requisites": 0, "payments": 0, "videos": 0}
    
    # Стандартный layout, если не указан
    default_layout = [
        [f"📄 Проверить документы ({counts['docs']})", f"💳 Выдать реквизиты ({counts['requisites']})"],
        [f"💰 Проверить оплату ({counts['payments']})", f"🎥 Проверить видео ({counts['videos']})"],
        ["📋 Список заявок"],
        ["⚙️ Управление реквизитами"]
    ]
    
    layout = layout or default_layout
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    
    for row in layout:
        markup.row(*[KeyboardButton(btn_text) for btn_text in row])
    
    return markup