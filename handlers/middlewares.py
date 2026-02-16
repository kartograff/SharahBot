from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
import database as db

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        if db.is_user_banned(user_id):
            if isinstance(event, Message):
                await event.answer("⛔ Доступ заблокирован. Обратитесь к администратору.")
            else:
                await event.answer("⛔ Доступ заблокирован", show_alert=True)
            return
        return await handler(event, data)