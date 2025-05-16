from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from states.verification import VerificationFSM
from keyboards.reply_common import cancel_keyboard
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from database.db import (
    create_verification,
    update_verification,
    set_verification_status,
    get_verification_status
)
from utils.media_saver import save_file


def get_continue_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("▶️ Продолжить"),
        KeyboardButton("❌ Отмена")
    )


def register_user_verification(dp: Dispatcher):

    @dp.message_handler(text="✅ Пройти верификацию")
    async def start_verification(msg: types.Message, state: FSMContext):
        create_verification(msg.from_user.id)
        await msg.answer(
            "🔐 Перед покупкой криптовалюты необходимо пройти верификацию.\n\nВы готовы начать?",
            reply_markup=get_continue_keyboard()
        )
        await VerificationFSM.waiting_agreement.set()

    @dp.message_handler(text="❌ Отмена", state="*")
    async def cancel_process(msg: types.Message, state: FSMContext):
        await state.finish()
        await msg.answer("❌ Верификация отменена.", reply_markup=types.ReplyKeyboardRemove())

    @dp.message_handler(text="▶️ Продолжить", state=VerificationFSM.waiting_agreement)
    async def step_agreement(msg: types.Message, state: FSMContext):
        await msg.answer(
            "⚠️ Важно: Никому не передавайте ваши документы и реквизиты.\nБудьте осторожны с мошенниками.",
            reply_markup=get_continue_keyboard()
        )
        await VerificationFSM.waiting_warning_ack.set()

    @dp.message_handler(text="▶️ Продолжить", state=VerificationFSM.waiting_warning_ack)
    async def step_warning(msg: types.Message, state: FSMContext):
        await msg.answer(
            "📷 Пожалуйста, загрузите:\n\n1. Фото паспорта с надписью 'Для обмена'\n2. Селфи с этим паспортом.",
            reply_markup=cancel_keyboard
        )
        await VerificationFSM.waiting_documents.set()

    @dp.message_handler(content_types=types.ContentType.PHOTO, state=VerificationFSM.waiting_documents)
    async def step_documents(msg: types.Message, state: FSMContext):
        data = await state.get_data()

        if "doc_photo" not in data:
            file_id = msg.photo[-1].file_id
            path = await save_file(msg.bot, file_id, "docs")
            await state.update_data(doc_photo=path)
            await msg.answer("✅ Паспорт получен. Теперь отправьте селфи.", reply_markup=cancel_keyboard)
            return

        file_id = msg.photo[-1].file_id
        selfie_path = await save_file(msg.bot, file_id, "docs")
        doc_path = data["doc_photo"]

        update_verification(msg.from_user.id, "doc_photo", doc_path)
        update_verification(msg.from_user.id, "selfie_photo", selfie_path, "new")

        await msg.answer("📬 Документы отправлены оператору. Ожидайте проверки.", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()

    @dp.message_handler(content_types=types.ContentType.PHOTO, state=VerificationFSM.waiting_payment_proof)
    async def step_payment(msg: types.Message, state: FSMContext):
        file_id = msg.photo[-1].file_id
        path = await save_file(msg.bot, file_id, "payments")
        update_verification(msg.from_user.id, "payment_proof", path, "paid_waiting")
        await msg.answer("📤 Чек отправлен оператору. Ожидайте подтверждения.")
        await state.finish()

    @dp.message_handler(content_types=types.ContentType.VIDEO, state=VerificationFSM.waiting_video)
    async def step_video(msg: types.Message, state: FSMContext):
        file_id = msg.video.file_id
        path = await save_file(msg.bot, file_id, "videos")
        update_verification(msg.from_user.id, "video", path, "video_waiting")
        await msg.answer("📤 Видео отправлено оператору. Ожидайте подтверждения.")
        await state.finish()

    # Резервный обработчик чека
    @dp.message_handler(content_types=types.ContentType.PHOTO)
    async def fallback_payment_handler(msg: types.Message):
        user_id = msg.from_user.id
        status = get_verification_status(user_id)
        if status != "paid_waiting":
            return

        path = await save_file(msg.bot, msg.photo[-1].file_id, "payments")
        update_verification(user_id, "payment_proof", path, "paid_waiting")
        await msg.answer("✅ Чек получен. Ожидайте подтверждения от оператора.")

    # Резервный обработчик видео
    @dp.message_handler(content_types=types.ContentType.VIDEO)
    async def fallback_video_handler(msg: types.Message):
        user_id = msg.from_user.id
        status = get_verification_status(user_id)
        if status != "video_waiting":
            return

        path = await save_file(msg.bot, msg.video.file_id, "videos")
        update_verification(user_id, "video", path, "video_waiting")
        await msg.answer("📤 Видео получено. Ожидайте подтверждения.")