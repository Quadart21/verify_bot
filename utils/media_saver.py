import os
from aiogram import Bot


BASE_DIR = "user_data"


async def save_file(bot: Bot, file_id: str, category: str, user_id: int = None) -> str:
    file = await bot.get_file(file_id)
    ext = file.file_path.split('.')[-1]

    # Путь до папки с категорией и user_id
    if user_id is not None:
        dir_path = os.path.join(BASE_DIR, category, str(user_id))
    else:
        dir_path = os.path.join(BASE_DIR, category)

    os.makedirs(dir_path, exist_ok=True)

    # Имя файла
    file_name = f"{file_id}.{ext}"
    file_path = os.path.join(dir_path, file_name)

    await bot.download_file(file.file_path, destination=file_path)
    return file_path
