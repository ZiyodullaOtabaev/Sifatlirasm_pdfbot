"""
Outer middleware for Maintenance Mode and User Ban enforcement.
Admins always bypass both checks cleanly.
"""
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from bot.config import ADMIN_IDS, ADMIN_ID
from bot.database import is_maintenance_mode, is_user_banned, get_user_language
from bot.i18n import t

logger = logging.getLogger(__name__)


def _is_admin_uid(user_id: int) -> bool:
    return (user_id in ADMIN_IDS) or (ADMIN_ID and user_id == ADMIN_ID)


class AccessControlMiddleware(BaseMiddleware):
    """Enforce maintenance mode and user ban status globally before handlers run."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        uid = user.id
        if _is_admin_uid(uid):
            return await handler(event, data)

        # 1. Maintenance Mode check
        if is_maintenance_mode():
            lang = get_user_language(uid) or "uz"
            msg_text = t("maintenance_text", lang)
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer(msg_text, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(msg_text, parse_mode="HTML")
            except Exception:
                pass
            return None

        # 2. Banned User check
        if is_user_banned(uid):
            lang = get_user_language(uid) or "uz"
            ban_text = t("banned_text", lang)
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer(ban_text, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(ban_text, parse_mode="HTML")
            except Exception:
                pass
            return None

        return await handler(event, data)
