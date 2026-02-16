import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import user, admin
from handlers.middlewares import BanCheckMiddleware
from utils import notification_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    init_db()

    dp.include_router(user.router)
    dp.include_router(admin.router)

    asyncio.create_task(notification_scheduler(bot))

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())