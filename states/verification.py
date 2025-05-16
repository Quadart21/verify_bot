from aiogram.dispatcher.filters.state import State, StatesGroup

class VerificationFSM(StatesGroup):
    waiting_agreement = State()
    waiting_warning_ack = State()
    waiting_documents = State()
    waiting_payment_proof = State()
    waiting_video = State()
