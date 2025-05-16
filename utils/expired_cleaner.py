import asyncio
from database.db import expire_old_verifications

async def expired_verification_cleaner():
    while True:
        expire_old_verifications()
        await asyncio.sleep(60)  # проверка каждую минуту
