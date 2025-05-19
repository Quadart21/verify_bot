from aiogram.dispatcher.filters.state import State, StatesGroup

class MailingFSM(StatesGroup):
    choose_type = State()
    enter_caption = State()
    waiting_file = State()
    enter_buttons = State()
    confirm_preview = State()
