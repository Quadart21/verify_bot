from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config import OPERATORS
from database.db import get_all_verifications, delete_verification
from keyboards.reply_operator import get_operator_menu


def register_operator_all_requests(dp: Dispatcher):

    @dp.message_handler(text="📋 Список заявок", user_id=OPERATORS)
    async def show_all_requests(msg: types.Message, state: FSMContext):
        # Исключаем заявки, которые уже завершены или подтверждены
        exclude_statuses = ("finished", "rejected", "video_ok")
        all_data = get_all_verifications()
        active = [v for v in all_data if v["status"] not in exclude_statuses]

        if not active:
            await msg.answer("📭 Нет зависших заявок.")
            return

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for v in active:
            kb.add(KeyboardButton(f"🗑 Удалить: {v['user_id']} ({v['status']})"))
        kb.add(KeyboardButton("🔙 Назад"))

        await state.set_state("awaiting_manual_delete")
        await msg.answer("📋 Все зависшие заявки:\n\nВыберите, какую удалить:", reply_markup=kb)

    @dp.message_handler(lambda msg: msg.text.startswith("🗑 Удалить:"), state="awaiting_manual_delete", user_id=OPERATORS)
    async def delete_request(msg: types.Message, state: FSMContext):
        try:
            user_id = int(msg.text.split(":")[1].split("(")[0].strip())
        except Exception:
            await msg.answer("⚠️ Неверный формат.")
            return

        delete_verification(user_id)
        await msg.answer(f"✅ Заявка пользователя {user_id} удалена.")
        await show_all_requests(msg, state)

    @dp.message_handler(text="🔙 Назад", state="awaiting_manual_delete", user_id=OPERATORS)
    async def back_to_menu(msg: types.Message, state: FSMContext):
        await state.finish()
        await msg.answer("↩ Возврат в меню оператора.", reply_markup=get_operator_menu())
