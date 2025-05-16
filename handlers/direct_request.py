from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database.db import (
    create_verification,
    update_verification,
    set_verification_status,
    get_all_requisites,
    is_verified
)
from utils.media_saver import save_file


def register_direct_request(dp: Dispatcher):

    @dp.message_handler(text="💳 Запросить реквизиты")
    async def request_requisites_direct(msg: types.Message, state: FSMContext):
        user_id = msg.from_user.id
        if not is_verified(user_id):
            await msg.answer("❌ Вы не прошли верификацию.")
            return

        create_verification(user_id)
        set_verification_status(user_id, "docs_ok", is_direct=True)  # Указываем прямой путь (без видео)

        requisites = get_all_requisites()
        if not requisites:
            await msg.answer("⚠️ Сейчас нет доступных реквизитов.")
            return

        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for r in requisites:
            kb.add(KeyboardButton(r[1]))
        kb.add(KeyboardButton("📝 Ввести вручную"))

        await state.set_state("choose_direct_requisite")
        await msg.answer("💳 Выберите способ оплаты:", reply_markup=kb)

    @dp.message_handler(state="choose_direct_requisite")
    async def select_direct_requisite(msg: types.Message, state: FSMContext):
        label = msg.text
        if label == "📝 Ввести вручную":
            await msg.answer("✏️ Введите реквизиты вручную:")
            await state.set_state("manual_direct_requisite")
            return

        for r in get_all_requisites():
            if r[1] == label:
                await msg.answer(
                    f"📨 Реквизиты:\n\n{r[2]}\n\n📸 Отправьте фото или скриншот оплаты.",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                await state.set_state("waiting_direct_payment_proof")
                return

        await msg.answer("⚠️ Реквизит не найден.")

    @dp.message_handler(state="manual_direct_requisite")
    async def manual_direct_requisite(msg: types.Message, state: FSMContext):
        await msg.answer(
            f"📨 Реквизиты:\n\n{msg.text}\n\n📸 Отправьте фото или скриншот оплаты.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state("waiting_direct_payment_proof")

    @dp.message_handler(content_types=types.ContentType.PHOTO, state="waiting_direct_payment_proof")
    async def save_direct_payment_proof(msg: types.Message, state: FSMContext):
        path = await save_file(msg.bot, msg.photo[-1].file_id, "payments")
        update_verification(msg.from_user.id, "payment_proof", path, "paid_waiting")
        await msg.answer("📤 Чек отправлен оператору. Ожидайте подтверждения.")
        await state.finish()
