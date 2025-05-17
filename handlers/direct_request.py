from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from utils.notifier import notify_group

from database.db import (
    is_verified,
    get_verification_status,
    create_requisite_request
)


def register_direct_request(dp: Dispatcher):

    @dp.message_handler(text="💳 Запросить реквизиты")
    async def request_requisites_direct(msg: types.Message, state: FSMContext):
        user_id = msg.from_user.id

        if not is_verified(user_id):
            await msg.answer("❌ Вы не прошли верификацию.")
            return

        current_status = get_verification_status(user_id)

        if current_status not in ("video_ok", "finished"):
            await msg.answer("⏳ Ваша заявка ещё не завершена. Ожидайте оператора.")
            return

        # логика создания заявки
        if not create_requisite_request(user_id):
            await msg.answer("⚠️ У вас уже есть активная заявка на получение реквизитов.\nОжидайте оператора.")
            return

        await msg.answer("📨 Запрос на реквизиты отправлен.\nОжидайте, оператор вышлет их вручную.")
        await notify_group(msg.bot, f"📬 Клиент {user_id} запросил реквизиты после верификации.")

