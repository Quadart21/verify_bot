import os
from uuid import uuid4

async def save_file(bot, file_id, folder):
    path = f"media/{folder}"
    os.makedirs(path, exist_ok=True)
    file = await bot.get_file(file_id)
    file_path = f"{path}/{uuid4()}.jpg"
    await bot.download_file(file.file_path, file_path)
    return file_path
