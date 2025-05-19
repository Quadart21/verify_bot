from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters import CommandStart
from aiogram.dispatcher import FSMContext

from config import OPERATORS
from utils.role_check import is_operator
from keyboards.reply_user import get_user_menu
from keyboards.reply_operator import get_operator_menu

from database.db import (
    add_user,
    is_user_verified,
    get_verification_data,
    get_pending_verifications_count
)


def register_start(dp: Dispatcher):
    @dp.message_handler(CommandStart(), state='*')
    async def start_cmd(message: types.Message, state: FSMContext):
        await state.finish()
        user_id = message.from_user.id

        add_user(user_id)
        args = message.get_args()

        if is_operator(user_id) and args:
            try:
                client_id_str, section = args.split("_")
                client_id = int(client_id_str)

                if section == "docs":
                    await open_docs_request(message, client_id, state)
                    return
                elif section == "payment":
                    await open_payment_request(message, client_id, state)
                    return
                elif section == "video":
                    await open_video_request(message, client_id, state)
                    return
            except:
                pass  # если аргументы некорректны — переходим в обычное меню

        if is_operator(user_id):
            counts = {
                "docs": get_pending_verifications_count("new"),
                "requisites": get_pending_verifications_count("docs_ok"),
                "payments": get_pending_verifications_count("paid_waiting"),
                "videos": get_pending_verifications_count("video_waiting"),
            }
            await message.answer("👨‍💼 Панель оператора:", reply_markup=get_operator_menu(counts))
        else:
            verified = is_user_verified(user_id)
            await message.answer("👤 Главное меню клиента:", reply_markup=get_user_menu(verified))


async def open_docs_request(msg: types.Message, client_id: int, state: FSMContext):
    data = get_verification_data(client_id)
    if not data or not data["doc_photo"] or not data["selfie_photo"]:
        await msg.answer("❌ У клиента нет загруженных документов.")
        return

    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    await state.update_data(current_user=client_id)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Подтвердить документы", "❌ Отклонить документы", "🔙 Назад")

    await msg.bot.send_photo(msg.chat.id, open(data["doc_photo"], "rb"), caption="📄 Паспорт")
    await msg.bot.send_photo(msg.chat.id, open(data["selfie_photo"], "rb"), caption="🤳 Селфи")
    await msg.answer("Выберите действие:", reply_markup=kb)
    await state.set_state("processing_document_user")


async def open_payment_request(msg: types.Message, client_id: int, state: FSMContext):
    data = get_verification_data(client_id)
    if not data or not data["payment_proof"]:
        await msg.answer("❌ У клиента нет загруженного чека.")
        return

    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    await state.update_data(current_user=client_id)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Подтвердить оплату", "❌ Отклонить оплату", "🔙 Назад")

    await msg.bot.send_photo(msg.chat.id, open(data["payment_proof"], "rb"), caption="💵 Чек об оплате")
    await msg.answer("Выберите действие:", reply_markup=kb)
    await state.set_state("processing_payment_user")


async def open_video_request(msg: types.Message, client_id: int, state: FSMContext):
    data = get_verification_data(client_id)
    if not data or not data["video"]:
        await msg.answer("❌ У клиента нет загруженного видео.")
        return

    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

    await state.update_data(current_user=client_id)

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Подтвердить видео", "❌ Отклонить видео", "🔙 Назад")

    await msg.bot.send_video(msg.chat.id, open(data["video"], "rb"), caption="🎥 Видео клиента")
    await msg.answer("Выберите действие:", reply_markup=kb)
    await state.set_state("processing_video_user")
