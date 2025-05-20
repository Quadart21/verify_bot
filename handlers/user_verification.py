from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher

from states.verification import VerificationFSM
from keyboards.reply_common import cancel_keyboard
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from keyboards.reply_user import get_user_menu
from utils.notifier import notify_group
from utils.media_saver import save_file
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import (
    create_verification,
    update_verification,
    set_verification_status,
    get_verification_status,
    is_verified
)


def get_continue_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("❌ Отмена"),
        KeyboardButton("▶️ Продолжить")
    )


def get_retry_keyboard(text="🔁 Повторить шаг"):
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton(text),
        KeyboardButton("🏠 В начало")
    )


def register_user_verification(dp: Dispatcher):

    @dp.message_handler(text="✅ Пройти верификацию")
    async def start_verification(msg: types.Message, state: FSMContext):
        create_verification(msg.from_user.id)
        await msg.answer(
            "👀 ВЕРИФИКАЦИЯ\n\nПеред отправкой средств клиент обязан пройти полную верификацию. Это защита от мошенничества и гарантия безопасности.\n\n🤫 Процедура верификации включает: \n\n- верификация документа\n- подтверждение платежной операции\n- видео-верификация",
            reply_markup=get_continue_keyboard()
        )
        await VerificationFSM.waiting_agreement.set()


    @dp.message_handler(text="Написать в поддержку", state="*")
    async def handle_support_request(msg: types.Message, state: FSMContext):
        await state.finish()

        keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔗 Онлайн-поддержка", url="https://t.me/bitcoinbox_support")
        )

        await msg.answer(
            "Если возникли сложности — не оставайтесь с ними один на один. Наша поддержка всегда рядом.",
            reply_markup=keyboard
        )

        await msg.answer("Выберите действие:", reply_markup=get_user_menu(is_verified(msg.from_user.id)))


    @dp.message_handler(text="❌ Отмена", state="*")
    async def handle_cancel(msg: types.Message, state: FSMContext):
        await state.finish()

        await msg.answer(
            "❌ Вы вернулись в начало.",
            reply_markup=get_user_menu(is_verified(msg.from_user.id))
        )

    @dp.message_handler(text="▶️ Продолжить", state=VerificationFSM.waiting_agreement)
    async def step_agreement(msg: types.Message, state: FSMContext):
        await msg.answer(
            "⚠️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ :\n\n"
            "• Переводы принимаются только с личных счетов физических лиц\n"
            "• Средства принимаются только от верифицированного лица\n"
            "• Несовпадение имени = возврат с комиссией\n"
            "• Попытка обмана = блокировка обслуживания\n\n"
            "🚨 ВАЖНАЯ ИНФОРМАЦИЯ 🚨\n\n"
            "Сегодня активно применяются схемы, где мошенники обманом заставляют людей покупать криптовалюту и переводить её им. Будьте бдительны!\n\n"
            "👎 Как это происходит:\n"
            "• Вам предлагают инвестиции с якобы высоким доходом и просят оплатить участие в криптовалюте.\n"
            "• Обещают быстрый заработок в интернете за минимальные усилия, но просят сначала перевести крипту.\n"
            "• Завлекают в сетевой маркетинг или финансовую пирамиду.\n"
            "• Приглашают на “работу кассиром”, где нужно покупать крипту от своего имени.\n\n"
            "🛡 Покупайте криптовалюту только для себя и только осознанно!",
            reply_markup=get_continue_keyboard()
        )
        await VerificationFSM.waiting_warning_ack.set()

    @dp.message_handler(text="▶️ Продолжить", state=VerificationFSM.waiting_warning_ack)
    async def step_warning(msg: types.Message, state: FSMContext):
        with open("img/2.jpg", "rb") as photo1:
            await msg.answer_photo(photo=photo1, caption="Фото-пример N1 — Паспорт или удостоверение личности со страницей и данными заявки")
        with open("img/1.jpg", "rb") as photo2:
            await msg.answer_photo(photo=photo2, caption="Фото-пример N2 — Селфи с документом в руках. Лицо и данные документа должны быть четко видны")

        await msg.answer(
            "Верификация документа:\n\n"
            "- Фото паспорта или ID + заявка\n"
            "- Селфи с этим же документом",
            reply_markup=cancel_keyboard
        )
        await VerificationFSM.waiting_documents.set()

    @dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT], state=VerificationFSM.waiting_documents)
    async def step_documents(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        file = msg.photo[-1] if msg.photo else msg.document
        file_id = file.file_id

        if "doc_photo" not in data:
            path = await save_file(msg.bot, file_id, "docs", msg.from_user.id)
            await state.update_data(doc_photo=path)
            await msg.answer("✅ Паспорт получен. Теперь отправьте селфи.", reply_markup=cancel_keyboard)
            return

        selfie_path = await save_file(msg.bot, file_id, "docs", msg.from_user.id)
        doc_path = data["doc_photo"]

        update_verification(msg.from_user.id, "doc_photo", doc_path)
        update_verification(msg.from_user.id, "selfie_photo", selfie_path)
        set_verification_status(msg.from_user.id, "new")

        await msg.answer("📬 Документы отправлены оператору. Ожидайте проверки.", reply_markup=types.ReplyKeyboardRemove())
        await notify_group(msg.bot, f"📄 Клиент {msg.from_user.id} загрузил паспорт.", user_id=msg.from_user.id)
        await state.finish()

    @dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT], state=VerificationFSM.waiting_payment_proof)
    async def step_payment(msg: types.Message, state: FSMContext):
        file = msg.photo[-1] if msg.photo else msg.document
        file_id = file.file_id
        path = await save_file(msg.bot, file_id, "payments", msg.from_user.id)
        update_verification(msg.from_user.id, "payment_proof", path)
        set_verification_status(msg.from_user.id, "paid_waiting")
        await msg.answer("📤 Чек отправлен оператору. Ожидайте подтверждения.")
        await notify_group(msg.bot, f"💵 Клиент {msg.from_user.id} отправил чек об оплате.", user_id=msg.from_user.id)
        await state.finish()

    @dp.message_handler(content_types=[types.ContentType.VIDEO, types.ContentType.DOCUMENT], state=VerificationFSM.waiting_video)
    async def step_video(msg: types.Message, state: FSMContext):
        file = msg.video or msg.document
        file_id = file.file_id
        path = await save_file(msg.bot, file_id, "videos", msg.from_user.id)
        update_verification(msg.from_user.id, "video", path)
        set_verification_status(msg.from_user.id, "video_waiting")
        await msg.answer("📤 Видео отправлено оператору. Ожидайте подтверждения.")
        await notify_group(msg.bot, f"🎥 Клиент {msg.from_user.id} отправил видео для верификации.", user_id=msg.from_user.id)
        await state.finish()

    # ==== Повторные шаги после отказа ====

    @dp.message_handler(text="📄 Загрузить документы заново")
    async def retry_documents(msg: types.Message, state: FSMContext):
        await state.finish()
        await state.reset_data()

        # Очистка старых данных
        update_verification(msg.from_user.id, "doc_photo", "")
        update_verification(msg.from_user.id, "selfie_photo", "")
        set_verification_status(msg.from_user.id, "draft")

        with open("img/2.jpg", "rb") as photo1:
            await msg.answer_photo(photo=photo1, caption="Фото-пример N1 — Паспорт или удостоверение личности со страницей и данными заявки")
        with open("img/1.jpg", "rb") as photo2:
            await msg.answer_photo(photo=photo2, caption="Фото-пример N2 — Селфи с документом в руках")

        await msg.answer(
            "🔁 Повторная верификация документа:\n\n"
            "- Отправьте фотографию документа (паспорт или ID)\n"
            "- Затем — селфи с ним",
            reply_markup=cancel_keyboard
        )
        await VerificationFSM.waiting_documents.set()

    @dp.message_handler(text="💵 Загрузить чек заново")
    async def retry_payment(msg: types.Message, state: FSMContext):
        await state.finish()
        await state.reset_data()

        # Очистка старого чека
        update_verification(msg.from_user.id, "payment_proof", "")
        set_verification_status(msg.from_user.id, "draft")

        await msg.answer("🔁 Повторная загрузка чека.\nПришлите скрин или фото чека:", reply_markup=cancel_keyboard)
        await VerificationFSM.waiting_payment_proof.set()

    @dp.message_handler(text="🎥 Загрузить видео заново")
    async def retry_video(msg: types.Message, state: FSMContext):
        await state.finish()
        await state.reset_data()

        # Очистка старого видео
        update_verification(msg.from_user.id, "video", "")
        set_verification_status(msg.from_user.id, "draft")

        await msg.answer("🔁 Повторная загрузка видео.\nПришлите видео по инструкции.", reply_markup=cancel_keyboard)
        await VerificationFSM.waiting_video.set()

    @dp.message_handler(text="🏠 В начало")
    async def back_to_start(msg: types.Message, state: FSMContext):
        await state.finish()
        await msg.answer(
            "🏠 Возврат в начало.\nНажмите кнопку ниже для старта верификации:",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("✅ Пройти верификацию"))
        )

    @dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT])
    async def fallback_payment_handler(msg: types.Message):
        user_id = msg.from_user.id
        status = get_verification_status(user_id)

        # Разрешаем вне FSM загрузку чека, если статус уже paid_waiting
        if status != "paid_waiting":
            return

        file = msg.photo[-1] if msg.photo else msg.document
        file_id = file.file_id
        path = await save_file(msg.bot, file_id, "payments", user_id)

        update_verification(user_id, "payment_proof", path)

        await msg.answer("✅ Чек получен. Ожидайте подтверждения от оператора.")
        await notify_group(msg.bot, f"💵 Клиент {user_id} отправил чек.", user_id=user_id)

    @dp.message_handler(content_types=[types.ContentType.VIDEO, types.ContentType.DOCUMENT])
    async def fallback_video_handler(msg: types.Message):
        user_id = msg.from_user.id
        status = get_verification_status(user_id)

        if status != "video_waiting":
            return

        file = msg.video or msg.document
        file_id = file.file_id
        path = await save_file(msg.bot, file_id, "videos", user_id)

        update_verification(user_id, "video", path)

        await msg.answer("📤 Видео получено. Ожидайте подтверждения.")
        await notify_group(msg.bot, f"🎥 Клиент {user_id} отправил видео.", user_id=user_id)
