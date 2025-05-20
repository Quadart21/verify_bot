from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from states.verification import VerificationFSM
from keyboards.reply_user import get_user_menu
from keyboards.reply_common import cancel_keyboard

from handlers.user_verification import resend_documents, resend_payment_proof, resend_video
from aiogram.dispatcher.storage import BaseStorage


def get_retry_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔁 Повторить шаг"), KeyboardButton("🏠 В начало"))
    return kb


async def ask_retry_step(bot, user_id: int, current_step: str, reason: str):
    
    await bot.send_message(
        user_id,
        f"❌ Ваш {current_step} отклонён.\nПричина: {reason}\n\nЧто вы хотите сделать?",
        reply_markup=get_retry_keyboard()
    )

    # получить Dispatcher и storage
    from aiogram import Dispatcher
    dp = Dispatcher.get_current()
    storage: BaseStorage = dp.storage

    # установить состояние и данные
    await storage.set_state(chat=user_id, user=user_id, state="awaiting_retry_decision")
    await storage.set_data(chat=user_id, user=user_id, data={"retry_step": current_step})


def register_retry_navigation(dp: Dispatcher):
    @dp.message_handler(text="🔁 Повторить шаг", state="awaiting_retry_decision")
    async def retry_step(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        step = data.get("retry_step")

        if step == "документ":
            await resend_documents(msg.bot, msg.from_user.id)
            await state.set_state(VerificationFSM.document)

        elif step == "оплата":
            await resend_payment_proof(msg.bot, msg.from_user.id)
            await state.set_state(VerificationFSM.payment)

        elif step == "видео":
            await resend_video(msg.bot, msg.from_user.id)
            await state.set_state(VerificationFSM.video)

    @dp.message_handler(text="🏠 В начало", state="awaiting_retry_decision")
    async def back_to_start(msg: types.Message, state: FSMContext):
        await state.finish()
        await msg.answer("🏠 Возврат в главное меню", reply_markup=get_user_menu())
