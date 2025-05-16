from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config import OPERATORS
from database.db import (
    get_all_requisites,
    add_requisite,
    update_requisite,
    delete_requisite,
    get_pending_verifications_count
)
from keyboards.reply_operator import get_operator_menu


def register_operator_requisites(dp: Dispatcher):

    @dp.message_handler(lambda msg: msg.text == "⚙️ Управление реквизитами", user_id=OPERATORS)
    async def manage_requisites(msg: types.Message, state: FSMContext):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("➕ Добавить реквизит", "✏️ Изменить", "❌ Удалить", "🔙 Назад")
        await msg.answer("🛠 Выберите действие с реквизитами:", reply_markup=kb)
        await state.set_state("manage_requisites")

    @dp.message_handler(lambda msg: msg.text == "➕ Добавить реквизит", state="manage_requisites", user_id=OPERATORS)
    async def add_requisite_start(msg: types.Message, state: FSMContext):
        await msg.answer("✍ Введите название (label) реквизита:")
        await state.set_state("add_requisite_label")

    @dp.message_handler(state="add_requisite_label", user_id=OPERATORS)
    async def add_requisite_label(msg: types.Message, state: FSMContext):
        await state.update_data(new_label=msg.text)
        await msg.answer("📨 Введите данные (details) реквизита:")
        await state.set_state("add_requisite_details")

    @dp.message_handler(state="add_requisite_details", user_id=OPERATORS)
    async def add_requisite_details(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        add_requisite(data["new_label"], msg.text)
        await msg.answer("✅ Реквизит добавлен.")
        await manage_requisites(msg, state)

    @dp.message_handler(lambda msg: msg.text == "✏️ Изменить", state="manage_requisites", user_id=OPERATORS)
    async def update_requisite_start(msg: types.Message, state: FSMContext):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for r in get_all_requisites():
            kb.add(KeyboardButton(f"{r[0]}: {r[1]}"))
        kb.add("🔙 Назад")
        await msg.answer("🔁 Выберите реквизит для изменения (по ID):", reply_markup=kb)
        await state.set_state("select_requisite_update")

    @dp.message_handler(state="select_requisite_update", user_id=OPERATORS)
    async def update_requisite_select(msg: types.Message, state: FSMContext):
        if msg.text == "🔙 Назад":
            await manage_requisites(msg, state)
            return
        try:
            req_id = int(msg.text.split(":")[0])
            await state.update_data(req_id=req_id)
            await msg.answer("✏️ Введите новое название:")
            await state.set_state("update_requisite_label")
        except:
            await msg.answer("⚠️ Введите ID реквизита в формате: `1: Название`.")

    @dp.message_handler(state="update_requisite_label", user_id=OPERATORS)
    async def update_requisite_label(msg: types.Message, state: FSMContext):
        await state.update_data(new_label=msg.text)
        await msg.answer("✏️ Введите новые данные:")
        await state.set_state("update_requisite_details")

    @dp.message_handler(state="update_requisite_details", user_id=OPERATORS)
    async def update_requisite_details(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        update_requisite(data["req_id"], data["new_label"], msg.text)
        await msg.answer("✅ Реквизит обновлён.")
        await manage_requisites(msg, state)

    @dp.message_handler(lambda msg: msg.text == "❌ Удалить", state="manage_requisites", user_id=OPERATORS)
    async def delete_requisite_start(msg: types.Message, state: FSMContext):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        for r in get_all_requisites():
            kb.add(KeyboardButton(f"{r[0]}: {r[1]}"))
        kb.add("🔙 Назад")
        await msg.answer("🗑 Выберите реквизит для удаления:", reply_markup=kb)
        await state.set_state("select_requisite_delete")

    @dp.message_handler(state="select_requisite_delete", user_id=OPERATORS)
    async def delete_requisite_confirm(msg: types.Message, state: FSMContext):
        if msg.text == "🔙 Назад":
            await manage_requisites(msg, state)
            return
        try:
            req_id = int(msg.text.split(":")[0])
            delete_requisite(req_id)
            await msg.answer("✅ Реквизит удалён.")
            await manage_requisites(msg, state)
        except:
            await msg.answer("⚠️ Введите ID реквизита в формате: `1: Название`.")

    @dp.message_handler(lambda msg: msg.text == "🔙 Назад", state="*", user_id=OPERATORS)
    async def go_back(msg: types.Message, state: FSMContext):
        await state.finish()
        counts = {
            "docs": get_pending_verifications_count("new"),
            "requisites": get_pending_verifications_count("docs_ok"),
            "payments": get_pending_verifications_count("paid_waiting"),
            "videos": get_pending_verifications_count("video_waiting"),
        }
        await msg.answer("↩ Возврат в меню оператора:", reply_markup=get_operator_menu(counts))
