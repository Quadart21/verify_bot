from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers.start import register_start
from handlers.user_verification import register_user_verification
from handlers.operator_documents import register_operator_documents
from handlers.operator_payments import register_operator_payments
from handlers.operator_video import register_operator_video
from handlers.operator_requisites import register_operator_requisites
from handlers.direct_request import register_direct_request


def main():
    # Инициализация базы данных
    init_db()

    # Настройка бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    # Регистрация всех обработчиков
    register_start(dp)
    register_user_verification(dp)
    register_operator_documents(dp)
    register_operator_payments(dp)
    register_operator_video(dp)
    register_operator_requisites(dp)
    register_direct_request(dp)

    # Запуск
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    main()