from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode

from config import OPERATORS
from database.db import get_all_users
from states.mailing import MailingFSM


def register_mailing(dp: Dispatcher):

    @dp.message_handler(text="📢 Рассылка", user_id=OPERATORS)
    async def start_mailing(msg: types.Message, state: FSMContext):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🖼 Фото", "🎥 Видео", "📝 Текст", "🔙 Назад")
        await msg.answer("Выберите тип рассылки:", reply_markup=kb)
        await state.set_state(MailingFSM.choose_type)

    @dp.message_handler(lambda m: m.text in ("🖼 Фото", "🎥 Видео", "📝 Текст"), state=MailingFSM.choose_type, user_id=OPERATORS)
    async def choose_type(msg: types.Message, state: FSMContext):
        type_map = {"🖼 Фото": "photo", "🎥 Видео": "video", "📝 Текст": "text"}
        await state.update_data(msg_type=type_map[msg.text])
        await msg.answer("✍ Введите текст сообщения (подпись, можно с *Markdown*):")
        await state.set_state(MailingFSM.enter_caption)

    @dp.message_handler(state=MailingFSM.enter_caption, user_id=OPERATORS)
    async def enter_caption(msg: types.Message, state: FSMContext):
        await state.update_data(caption=msg.text)
        data = await state.get_data()
        msg_type = data["msg_type"]

        if msg_type == "text":
            await prompt_buttons(msg)
        else:
            await msg.answer("📎 Пришлите файл:")
            await state.set_state(MailingFSM.waiting_file)

    @dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.VIDEO], state=MailingFSM.waiting_file, user_id=OPERATORS)
    async def receive_file(msg: types.Message, state: FSMContext):
        file_id = msg.photo[-1].file_id if msg.content_type == "photo" else msg.video.file_id
        await state.update_data(file_id=file_id)
        await prompt_buttons(msg)

    async def prompt_buttons(msg: types.Message):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("⛔ Без кнопок")
        await msg.answer(
            "➕ При необходимости, введите inline-кнопки в формате:\n\n"
            "`Кнопка 1 - https://example.com`\n"
            "`Кнопка 2 - https://telegram.org`\n\n"
            "Или нажмите ⛔ Без кнопок",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
        await MailingFSM.enter_buttons.set()

    @dp.message_handler(text="⛔ Без кнопок", state=MailingFSM.enter_buttons, user_id=OPERATORS)
    async def skip_buttons(msg: types.Message, state: FSMContext):
        await state.update_data(buttons=None)
        await show_preview(msg, state)

    @dp.message_handler(state=MailingFSM.enter_buttons, user_id=OPERATORS)
    async def parse_buttons(msg: types.Message, state: FSMContext):
        markup = InlineKeyboardMarkup()
        for line in msg.text.strip().splitlines():
            if "-" in line:
                label, url = line.split("-", 1)
                markup.add(InlineKeyboardButton(label.strip(), url=url.strip()))
        await state.update_data(buttons=markup)
        await show_preview(msg, state)

    async def show_preview(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        caption = data.get("caption", "")
        msg_type = data.get("msg_type")
        file_id = data.get("file_id", None)
        markup = data.get("buttons", None)

        preview_kb = ReplyKeyboardMarkup(resize_keyboard=True)
        preview_kb.add(KeyboardButton("✅ Подтвердить рассылку"), KeyboardButton("🔙 Назад"))

        if msg_type == "text":
            await msg.answer(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        elif msg_type == "photo":
            await msg.bot.send_photo(msg.chat.id, file_id, caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        elif msg_type == "video":
            await msg.bot.send_video(msg.chat.id, file_id, caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)

        await msg.answer("👆 Так будет выглядеть сообщение.\nПодтвердить отправку?", reply_markup=preview_kb)
        await state.set_state(MailingFSM.confirm_preview)

    @dp.message_handler(text="✅ Подтвердить рассылку", state=MailingFSM.confirm_preview, user_id=OPERATORS)
    async def confirm_send(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        caption = data.get("caption", "")
        msg_type = data.get("msg_type")
        file_id = data.get("file_id", None)
        markup = data.get("buttons", None)

        users = get_all_users()
        count = 0
        for uid in users:
            try:
                if msg_type == "text":
                    await msg.bot.send_message(uid, caption, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
                elif msg_type == "photo":
                    await msg.bot.send_photo(uid, file_id, caption=caption, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
                elif msg_type == "video":
                    await msg.bot.send_video(uid, file_id, caption=caption, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
                count += 1
            except:
                continue

        await msg.answer(f"✅ Рассылка завершена. Отправлено {count} пользователям.", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()

    @dp.message_handler(text="🔙 Назад", state=MailingFSM.confirm_preview, user_id=OPERATORS)
    async def go_back_to_edit(msg: types.Message, state: FSMContext):
        await msg.answer("✍ Введите новый текст подписи или отправьте новый файл.",
                         reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("⛔ Без кнопок"))
        await state.set_state(MailingFSM.enter_caption)
