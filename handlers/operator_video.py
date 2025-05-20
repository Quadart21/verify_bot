from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from config import OPERATORS
from database.db import (
    get_pending_verifications,
    get_verification_data,
    set_verification_status,
    set_user_verified,
    get_pending_verifications_count,
    is_verified
    
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from keyboards.reply_operator import get_operator_menu
from keyboards.reply_user import get_retry_keyboard, get_user_menu


def register_operator_video(dp: Dispatcher):

    @dp.message_handler(lambda msg: msg.text.startswith("🎥 Проверить видео"), user_id=OPERATORS)
    async def show_video_list(msg: types.Message, state: FSMContext):
        queue = list(set(get_pending_verifications("video_waiting")))
        if not queue:
            await msg.answer("📭 Нет видео на проверку.")
            return

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for uid in queue:
            kb.add(KeyboardButton(f"Видео: {uid}"))
        kb.add(KeyboardButton("🔙 Назад"))
        await state.set_state("awaiting_video_selection")
        await msg.answer("🎥 Выберите клиента для просмотра видео:", reply_markup=kb)

    @dp.message_handler(lambda msg: msg.text.startswith("Видео:"), state="awaiting_video_selection", user_id=OPERATORS)
    async def select_video_user(msg: types.Message, state: FSMContext):
        try:
            user_id = int(msg.text.replace("Видео:", "").strip())
        except ValueError:
            await msg.answer("⚠️ Неверный формат.")
            return

        verification = get_verification_data(user_id)
        if not verification or not verification["video"]:
            await msg.answer("❌ У пользователя нет видео.")
            return

        await state.update_data(current_user=user_id)

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("✅ Подтвердить видео", "❌ Отклонить видео", "🔙 Назад")

        video_path = verification["video"]
        if video_path.lower().endswith((".mp4", ".mov", ".mkv")):
            await msg.bot.send_video(msg.chat.id, open(video_path, "rb"), caption="🎥 Видео клиента")
        else:
            await msg.bot.send_document(msg.chat.id, open(video_path, "rb"), caption="🎥 Видео клиента")

        await msg.answer("Выберите действие:", reply_markup=kb)
        await state.set_state("processing_video_user")

    @dp.message_handler(text="✅ Подтвердить видео", state="processing_video_user", user_id=OPERATORS)
    async def approve_video(msg: types.Message, state: FSMContext):
        user_id = (await state.get_data())["current_user"]
        set_verification_status(user_id, "video_ok")
        set_user_verified(user_id)

        await msg.bot.send_message(
            user_id,
            "🔄 Благодарим Вас за успешное прохожлдение верификации.\n\n✔️ Отправили вашу заявку на выплату.\n\n⚠️ Информирую, что для дальнейших обменов от Вас потребуется только подтверждение оплаты в виде квитанции.\n\n👍 Будем ждать вас снова!"

        )

        await msg.answer("Выберите действие:", reply_markup=get_user_menu(is_verified(msg.from_user.id)))

        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("✅ Верификация клиента завершена.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(counts))

    @dp.message_handler(text="❌ Отклонить видео", state="processing_video_user", user_id=OPERATORS)
    async def reject_video_start(msg: types.Message, state: FSMContext):
        await msg.answer("✏️ Введите причину отклонения видео:")
        await state.set_state("awaiting_video_reject_reason")

    @dp.message_handler(state="awaiting_video_reject_reason", user_id=OPERATORS)
    async def reject_video_finish(msg: types.Message, state: FSMContext):
        reason = msg.text
        user_id = (await state.get_data())["current_user"]

        set_verification_status(user_id, "rejected", reason)

        # Уведомление клиента
        await msg.bot.send_message(
            user_id,
            f"❌ Видео отклонено.\nПричина: {reason}\n\nХотите загрузить видео заново или вернуться в начало?",
            reply_markup=get_retry_keyboard("🎥 Загрузить видео заново")
        )

        # Завершение FSM и возврат в меню оператора
        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("📛 Видео отклонено.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(counts))

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