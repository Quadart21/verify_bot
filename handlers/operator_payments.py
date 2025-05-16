from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from config import OPERATORS
from database.db import (
    get_pending_verifications,
    get_verification_data,
    set_verification_status,
    get_all_requisites,
    get_pending_verifications_count,
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from keyboards.reply_operator import get_operator_menu


def register_operator_payments(dp: Dispatcher):

    @dp.message_handler(lambda msg: msg.text.startswith("💳 Выдать реквизиты"), user_id=OPERATORS)
    async def show_requisites_list(msg: types.Message, state: FSMContext):
        queue = get_pending_verifications("docs_ok")
        if not queue:
            await msg.answer("📭 Нет клиентов, ожидающих реквизиты.")
            return

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for uid in queue:
            kb.add(KeyboardButton(f"Реквизиты: {uid}"))
        kb.add(KeyboardButton("🔙 Назад"))
        await state.set_state("awaiting_requisites_selection")
        await msg.answer("👤 Выберите клиента для выдачи реквизита:", reply_markup=kb)

    @dp.message_handler(lambda msg: msg.text.startswith("Реквизиты:"), state="awaiting_requisites_selection", user_id=OPERATORS)
    async def select_requisite_user(msg: types.Message, state: FSMContext):
        try:
            user_id = int(msg.text.replace("Реквизиты:", "").strip())
        except ValueError:
            await msg.answer("⚠️ Неверный формат.")
            return

        await state.update_data(current_user=user_id)

        requisites = get_all_requisites()
        if not requisites:
            await msg.answer("❗ Нет доступных реквизитов.")
            return

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for r in requisites:
            kb.add(KeyboardButton(r[1]))
        kb.add(KeyboardButton("📝 Ввести вручную"), KeyboardButton("🔙 Назад"))

        await state.set_state("awaiting_requisite_selection")
        await msg.answer(f"👤 Клиент: {user_id}\nВыберите или введите реквизит:", reply_markup=kb)

    @dp.message_handler(state="awaiting_requisite_selection", user_id=OPERATORS)
    async def choose_or_enter_requisite(msg: types.Message, state: FSMContext):
        if msg.text == "📝 Ввести вручную":
            await msg.answer("Введите реквизиты вручную:")
            await state.set_state("awaiting_requisite_manual")
        elif msg.text == "🔙 Назад":
            await show_requisites_list(msg, state)
        else:
            label = msg.text
            for r in get_all_requisites():
                if r[1] == label:
                    details = r[2]
                    await send_requisite_to_user(msg, state, details)
                    return
            await msg.answer("⚠️ Реквизит не найден.")

    @dp.message_handler(state="awaiting_requisite_manual", user_id=OPERATORS)
    async def enter_manual_requisite(msg: types.Message, state: FSMContext):
        await send_requisite_to_user(msg, state, msg.text)

    async def send_requisite_to_user(msg: types.Message, state: FSMContext, text: str):
        user_id = (await state.get_data())["current_user"]
        set_verification_status(user_id, "paid_waiting")

        await msg.bot.send_message(
            user_id,
            f"💳 Реквизиты для оплаты:\n\n{text}\n\n"
            "Пожалуйста, отправьте фото или скриншот чека после оплаты."
        )

        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("✅ Реквизит выслан клиенту.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(counts))

    @dp.message_handler(lambda msg: msg.text.startswith("💰 Проверить оплату"), user_id=OPERATORS)
    async def show_payment_list(msg: types.Message, state: FSMContext):
        queue = get_pending_verifications("paid_waiting")
        if not queue:
            await msg.answer("📭 Нет оплат на проверку.")
            return

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for uid in queue:
            kb.add(KeyboardButton(f"Оплата: {uid}"))
        kb.add(KeyboardButton("🔙 Назад"))
        await state.set_state("awaiting_payment_selection")
        await msg.answer("💵 Выберите заявку для проверки:", reply_markup=kb)

    @dp.message_handler(lambda msg: msg.text.startswith("Оплата:"), state="awaiting_payment_selection", user_id=OPERATORS)
    async def select_payment_user(msg: types.Message, state: FSMContext):
        try:
            user_id = int(msg.text.replace("Оплата:", "").strip())
        except ValueError:
            await msg.answer("⚠️ Неверный формат.")
            return

        verification = get_verification_data(user_id)
        if not verification or not verification["payment_proof"]:
            await msg.answer("❌ У пользователя нет чека.")
            return

        await state.update_data(current_user=user_id)

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("✅ Подтвердить оплату", "❌ Отклонить оплату", "🔙 Назад")

        await msg.bot.send_photo(msg.chat.id, open(verification["payment_proof"], "rb"), caption="💵 Чек об оплате")
        await msg.answer("Выберите действие:", reply_markup=kb)
        await state.set_state("processing_payment_user")

    @dp.message_handler(text="✅ Подтвердить оплату", state="processing_payment_user", user_id=OPERATORS)
    async def approve_payment(msg: types.Message, state: FSMContext):
        user_id = (await state.get_data())["current_user"]
        set_verification_status(user_id, "video_waiting")
        await msg.bot.send_message(user_id, "✅ Оплата подтверждена. Пришлите видео по инструкции.")
        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("✅ Оплата подтверждена.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(counts))

    @dp.message_handler(text="❌ Отклонить оплату", state="processing_payment_user", user_id=OPERATORS)
    async def reject_payment(msg: types.Message, state: FSMContext):
        await msg.answer("✏️ Введите причину отклонения оплаты:")
        await state.set_state("awaiting_payment_reject_reason")

    @dp.message_handler(state="awaiting_payment_reject_reason", user_id=OPERATORS)
    async def reject_payment_finish(msg: types.Message, state: FSMContext):
        reason = msg.text
        user_id = (await state.get_data())["current_user"]
        set_verification_status(user_id, "rejected", reason)
        await msg.bot.send_message(user_id, f"❌ Оплата отклонена.\nПричина: {reason}")
        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("📛 Оплата отклонена.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(counts))

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
