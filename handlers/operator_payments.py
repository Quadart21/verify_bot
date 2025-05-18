from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from config import OPERATORS
from database.db import (
    get_pending_verifications,
    get_verification_data,
    get_verification_status,
    set_verification_status,
    get_pending_verifications_count,
    get_pending_requisite_requests,
    mark_requisite_request_done,
    update_verification,
    is_verified
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from keyboards.reply_operator import get_operator_menu


def register_operator_payments(dp: Dispatcher): 

    @dp.message_handler(lambda msg: msg.text.startswith("💳 Выдать реквизиты"), user_id=OPERATORS)
    async def show_requisites_list(msg: types.Message, state: FSMContext):
        # Только клиенты на этапе docs_ok или с активным запросом
        uids_requests = get_pending_requisite_requests()
        uids_waiting = get_pending_verifications("docs_ok")

        # Исключить из ожидания тех, кто уже создал заявку на реквизиты
        uids_waiting = list(set(uids_waiting) - set(uids_requests))
        queue = uids_requests + uids_waiting

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

        current_status = get_verification_status(user_id)
        if current_status not in ("docs_ok", "video_ok", "finished"):
            await msg.answer("❗ Пользователь уже получил реквизиты или недоступен.")
            return

        await state.update_data(current_user=user_id)
        await msg.answer("✍ Введите реквизиты вручную:")
        await state.set_state("awaiting_requisite_manual")

    @dp.message_handler(state="awaiting_requisite_manual", user_id=OPERATORS)
    async def enter_manual_requisite(msg: types.Message, state: FSMContext):
        user_id = (await state.get_data())["current_user"]

        # Очистить старый чек и установить новый статус
        update_verification(user_id, "payment_proof", "", "paid_waiting")
        mark_requisite_request_done(user_id)

        await msg.bot.send_message(
            user_id,
            f"📨 Ваши реквизиты для оплаты:\n\n{msg.text}\n\n"
            "- После оплаты, покупатель предоставляет фото или скриншот экрана, на котором зафиксирован перевод средств (платёжное поручение, операция в онлайн-банке и т.д.) с чётким отображением :\n • Имени отправителя\n • Счета отправителя\n • Суммы\n • Даты и времени перевода"
        )


        await state.finish()
        await msg.answer("✅ Реквизит отправлен клиенту.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(_get_counts()))

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

        proof_path = verification["payment_proof"]
        if proof_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            await msg.bot.send_photo(msg.chat.id, open(proof_path, "rb"), caption="💵 Чек об оплате")
        else:
            await msg.bot.send_document(msg.chat.id, open(proof_path, "rb"), caption="💵 Чек об оплате")

        await msg.answer("Выберите действие:", reply_markup=kb)
        await state.set_state("processing_payment_user")

    @dp.message_handler(text="✅ Подтвердить оплату", state="processing_payment_user", user_id=OPERATORS)
    async def approve_payment(msg: types.Message, state: FSMContext):
        user_id = (await state.get_data())["current_user"]
        verification = get_verification_data(user_id)

    # Если пользователь уже верифицирован — не направляем его на видео
        if is_verified(user_id) or get_verification_status(user_id) in ("video_ok", "finished"):
            set_verification_status(user_id, "finished")
            await msg.bot.send_message(user_id, "✅ Спасибо! Оплата подтверждена. Мы обработаем вашу заявку в ближайшее время.")
        elif verification and verification.get("video") == "SKIP":
            set_verification_status(user_id, "finished")
            await msg.bot.send_message(user_id, "✅ Спасибо, мы обрабатываем вашу заявку. Ожидайте.")
        else:
            set_verification_status(user_id, "video_waiting")
            await msg.bot.send_message(user_id,"Видео-верификация : \n\n- краткое видео, на котором клиент держит в руках свой документ и устройство (телефон/планшет) с открытой квитанцией перевода на наш адрес, а так же со страницей заявки, на которой видно номер и реквизиты обмена.\n- произност следующий текст : \n\n\"Я Петров Петр Петрович, покупаю активы на сайте обменника bitcoinbox.io, номер обмена № 1234, для своего личного пользования и за свои личные денежные средства. Никто не просит и не заставляет меня это делать. О всех рисках предупрежден и совершаю это осознанно\"\n\n⚠️ ВАЖНО : \n\n- Вы должны быть одни в кадре — никто не должен находиться рядом, подсказывать или вмешиваться\n- Хорошее освещение и четкость — убедитесь, что ваше лицо и документ хорошо видны.\n- Без масок, очков, фильтров и монтажей — запрещается использовать какие-либо фильтры, скрывающие внешность, а также записывать видео заранее или монтировать.\n- Срок действия — видео действительно только в день записи.")

        await state.finish()
        await msg.answer("✅ Оплата подтверждена.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(_get_counts()))

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
        await msg.answer("📛 Оплата отклонена.\n↩ Возврат в меню оператора.", reply_markup=get_operator_menu(_get_counts()))

    @dp.message_handler(text="🔙 Назад", state="*", user_id=OPERATORS)
    async def go_back(msg: types.Message, state: FSMContext):
        await state.finish()
        await msg.answer("↩ Возврат в меню оператора.", reply_markup=get_operator_menu(_get_counts()))


def _get_counts():
    return {
        "docs": get_pending_verifications_count("new"),
        "requisites": get_pending_verifications_count("docs_ok"),
        "payments": get_pending_verifications_count("paid_waiting"),
        "videos": get_pending_verifications_count("video_waiting"),
    }
