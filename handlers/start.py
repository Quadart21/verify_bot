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
    get_pending_verifications_count
)


def register_start(dp: Dispatcher):
    @dp.message_handler(CommandStart(), state='*')
    async def start_cmd(message: types.Message, state: FSMContext):
        await state.finish()
        user_id = message.from_user.id

        add_user(user_id)

        if is_operator(user_id):
            # Подсчёт количества заявок по статусу
            counts = {
                "docs": get_pending_verifications_count("new"),
                "requisites": get_pending_verifications_count("docs_ok"),
                "payments": get_pending_verifications_count("paid_waiting"),
                "videos": get_pending_verifications_count("video_waiting"),
            }

            await message.answer("👨‍💼 Панель оператора:", reply_markup=get_operator_menu(counts))

        else:
            verified = is_user_verified(user_id)
            await message.answer(
                "👤 Главное меню клиента:",
                reply_markup=get_user_menu(verified)
            )
