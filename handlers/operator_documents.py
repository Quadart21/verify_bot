from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from config import OPERATORS
from database.db import (
    get_pending_verifications,
    get_verification_data,
    set_verification_status,
    get_pending_verifications_count,
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from keyboards.reply_operator import get_operator_menu
from keyboards.reply_user import get_retry_keyboard


def register_operator_documents(dp: Dispatcher):

    @dp.message_handler(lambda msg: msg.text.startswith("📄 Проверить документы"), user_id=OPERATORS)
    async def show_documents_list(msg: types.Message, state: FSMContext):
        users = list(set(get_pending_verifications("new")))
        if not users:
            await msg.answer("📭 Нет заявок на проверку документов.")
            return

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for uid in users:
            kb.add(KeyboardButton(f"Заявка: {uid}"))
        kb.add(KeyboardButton("🔙 Назад"))

        await state.set_state("awaiting_document_selection")
        await msg.answer("👥 Выберите заявку для проверки:", reply_markup=kb)

    @dp.message_handler(lambda msg: msg.text.startswith("Заявка:"), state="awaiting_document_selection", user_id=OPERATORS)
    async def select_document_user(msg: types.Message, state: FSMContext):
        try:
            user_id = int(msg.text.replace("Заявка:", "").strip())
        except ValueError:
            await msg.answer("⚠️ Неверный формат.")
            return

        verification = get_verification_data(user_id)
        if not verification or not verification["doc_photo"]:
            await msg.answer("❌ У пользователя нет загруженных документов.")
            return

        await state.update_data(current_user=user_id)

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("✅ Подтвердить документы", "❌ Отклонить документы", "🔙 Назад")

        doc_path = verification["doc_photo"]
        selfie_path = verification["selfie_photo"]

        if doc_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            await msg.bot.send_photo(msg.chat.id, open(doc_path, "rb"), caption="📄 Паспорт")
        else:
            await msg.bot.send_document(msg.chat.id, open(doc_path, "rb"), caption="📄 Паспорт")

        if selfie_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            await msg.bot.send_photo(msg.chat.id, open(selfie_path, "rb"), caption="🤳 Селфи")
        else:
            await msg.bot.send_document(msg.chat.id, open(selfie_path, "rb"), caption="🤳 Селфи")

        await msg.answer("Выберите действие:", reply_markup=kb)
        await state.set_state("processing_document_user")

    @dp.message_handler(text="✅ Подтвердить документы", state="processing_document_user", user_id=OPERATORS)
    async def approve_docs(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        user_id = data["current_user"]
        set_verification_status(user_id, "docs_ok")
        await msg.bot.send_message(user_id, "✅ Ваши документы одобрены. Ожидайте реквизиты для оплаты от оператора.")
        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("✅ Документы подтверждены.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(counts))

    @dp.message_handler(text="❌ Отклонить документы", state="processing_document_user", user_id=OPERATORS)
    async def reject_docs_start(msg: types.Message, state: FSMContext):
        await msg.answer("✏️ Введите причину отклонения:")
        await state.set_state("awaiting_document_reject_reason")

    @dp.message_handler(state="awaiting_document_reject_reason", user_id=OPERATORS)
    async def reject_docs_finish(msg: types.Message, state: FSMContext):
        reason = msg.text
        data = await state.get_data()
        user_id = data["current_user"]

        set_verification_status(user_id, "rejected", reason)

        # Уведомление клиента
        await msg.bot.send_message(
            user_id,
            f"❌ Ваши документы отклонены.\nПричина: {reason}\n\nХотите загрузить документы заново или вернуться в начало?",
            reply_markup=get_retry_keyboard("📄 Загрузить документы заново")
        )

        # Завершение FSM и возврат панели оператору
        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("📛 Документы отклонены.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(counts))


    @dp.message_handler(text="🔙 Назад", state="*", user_id=OPERATORS)
    async def go_back(msg: types.Message, state: FSMContext):
        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("↩ Возврат в меню оператора.", reply_markup=get_operator_menu(counts))