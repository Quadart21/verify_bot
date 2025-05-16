from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from database.db import (
    create_verification,
    set_verification_status,
    is_verified,
    get_verification_status,
)


def register_direct_request(dp: Dispatcher):

    @dp.message_handler(text="💳 Запросить реквизиты")
    async def request_requisites_direct(msg: types.Message, state: FSMContext):
        user_id = msg.from_user.id

        if not is_verified(user_id):
            await msg.answer("❌ Вы не прошли верификацию.")
            return

        current_status = get_verification_status(user_id)

        if current_status in ("docs_ok", "paid_waiting", "video_waiting"):
            await msg.answer("⏳ Ваша заявка уже находится в обработке. Ожидайте оператора.")
            return

        # создаём новую заявку даже если прошёл старый путь ранее
        create_verification(user_id)
        set_verification_status(user_id, "docs_ok", is_direct=True)

        await msg.answer("📨 Запрос на реквизиты отправлен.\nОжидайте, оператор вышлет их вручную.")
