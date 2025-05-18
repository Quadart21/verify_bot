from aiogram import types 
from aiogram.dispatcher import FSMContext, Dispatcher

from states.verification import VerificationFSM

from keyboards.reply_common import cancel_keyboard

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from utils.notifier import notify_group

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
            "👀 ВЕРИФИКАЦИЯ\n\nПеред отправкой средств клиент обязан пройти полную верификацию. Это защита от мошенничества и гарантия безопасности.\n\n🤫 Процедура верификации включает: \n\n- верификация документа\n- подтверждение платежной операции\n- видео-верификация",
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
            "⚠️ ОБЯЗАТЕЛЬНО К ПРОЧТЕНИЮ :\n\n• Переводы принимаются только с личных счетов физических лиц\n• Средства принимаются только от верифицированного лица\n• Несовпадение имени = возврат с комиссией\n• Попытка обмана = блокировка обслуживания\n\n🚨 ВАЖНАЯ ИНФОРМАЦИЯ 🚨\n\nСегодня активно применяются схемы, где мошенники обманом заставляют людей покупать криптовалюту и переводить её им. Будьте бдительны!\n\n👎 Как это происходит:\n\n• Вам предлагают инвестиции с якобы высоким доходом и просят оплатить участие в криптовалюте.\n• Обещают быстрый заработок в интернете за минимальные усилия, но просят сначала перевести крипту.\n• Завлекают в сетевой маркетинг или финансовую пирамиду, где вступительный взнос требуется оплатить в криптовалюте.\n• Приглашают на “работу кассиром”, где якобы нужно закупать крипту за свои деньги для «компании» или «клиентов».\n\n⚠️ Запомните:\n\n• Никакие реальные инвестиционные компании не просят переводить личные средства третьим лицам через покупку криптовалюты.\n• Никогда не покупайте крипту для передачи кому-то, даже если это кажется выгодным или срочным.\n• Не переводите крипту незнакомым людям, даже если они представляются сотрудниками известных брендов, бирж или банков.\n\n👀 Если вы сами оплачиваете сделку, но покупаете криптовалюту “по просьбе другого человека” — вы можете стать жертвой мошенников.\nВ итоге вы потеряете свои деньги без шанса вернуть их обратно.\n\n🛡 Покупайте криптовалюту только для себя и только осознанно!",
            reply_markup=get_continue_keyboard()
        )
        await VerificationFSM.waiting_warning_ack.set()

    @dp.message_handler(text="▶️ Продолжить", state=VerificationFSM.waiting_warning_ack)
    async def step_warning(msg: types.Message, state: FSMContext):
        # Отправляем фото-пример 1
        with open("img/2.jpg", "rb") as photo1:
            await msg.answer_photo(
                photo=photo1,
                caption="Фото-пример N1 — Паспорт или удостоверение личности со страницей и данными заявки"
            )
        # Отправляем фото-пример 2
        with open("img/1.jpg", "rb") as photo2:
            await msg.answer_photo(
                photo=photo2,
                caption="Фото-пример N2 — Селфи с документом в руках. Лицо и данные документа должны быть четко видны"
            )
        # Инструкция
        await msg.answer(
            "Верификация документа :\n\n- Фотография паспорта или удостоверения личности со страницей и данными заявки (см. пример выше)\n\n- Селфи с документом в руках — лицо и данные документа должны быть четко видны (см. пример выше)",
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
        update_verification(msg.from_user.id, "selfie_photo", selfie_path, "new")

        await msg.answer("📬 Документы отправлены оператору. Ожидайте проверки.", reply_markup=types.ReplyKeyboardRemove())
        await notify_group(msg.bot, f"📄 Клиент {msg.from_user.id} загрузил паспорт.")
        await state.finish()

    @dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT], state=VerificationFSM.waiting_payment_proof)
    async def step_payment(msg: types.Message, state: FSMContext):
        file = msg.photo[-1] if msg.photo else msg.document
        file_id = file.file_id
        path = await save_file(msg.bot, file_id, "payments", msg.from_user.id)
        update_verification(msg.from_user.id, "payment_proof", path, "paid_waiting")
        await msg.answer("📤 Чек отправлен оператору. Ожидайте подтверждения.")
        await notify_group(msg.bot, f"💵 Клиент {msg.from_user.id} отправил чек об оплате.")
        await state.finish()

    @dp.message_handler(content_types=[types.ContentType.VIDEO, types.ContentType.DOCUMENT], state=VerificationFSM.waiting_video)
    async def step_video(msg: types.Message, state: FSMContext):
        file = msg.video or msg.document
        file_id = file.file_id
        path = await save_file(msg.bot, file_id, "videos", msg.from_user.id)
        update_verification(msg.from_user.id, "video", path, "video_waiting")
        await msg.answer("📤 Видео отправлено оператору. Ожидайте подтверждения.")
        await notify_group(msg.bot, f"🎥 Клиент {msg.from_user.id} отправил видео для верификации.")
        await state.finish()

    @dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT])
    async def fallback_payment_handler(msg: types.Message):
        user_id = msg.from_user.id
        status = get_verification_status(user_id)
        if status != "paid_waiting":
            return

        file = msg.photo[-1] if msg.photo else msg.document
        path = await save_file(msg.bot, file.file_id, "payments", user_id)
        update_verification(user_id, "payment_proof", path, "paid_waiting")
        await msg.answer("✅ Чек получен. Ожидайте подтверждения от оператора.")
        await notify_group(msg.bot, f"💵 Клиент {user_id} отправил чек.")

    @dp.message_handler(content_types=[types.ContentType.VIDEO, types.ContentType.DOCUMENT])
    async def fallback_video_handler(msg: types.Message):
        user_id = msg.from_user.id
        status = get_verification_status(user_id)
        if status != "video_waiting":
            return

        file = msg.video or msg.document
        path = await save_file(msg.bot, file.file_id, "videos", user_id)
        update_verification(user_id, "video", path, "video_waiting")
        await msg.answer("📤 Видео получено. Ожидайте подтверждения.")
        await notify_group(msg.bot, f"🎥Клиент {user_id} отправил видео.")
