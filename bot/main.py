"""
Bot entry point — aiogram 3.x dispatcher setup and polling.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN, ADMIN_IDS, ADMIN_ID
from bot.database import db_init
from bot.handlers import get_all_routers
from bot.utils.cleanup import cleanup_worker, retention_worker, update_bot_description_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Initialize and start the bot."""
    db_init()
    logger.info("Database initialized")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Global Maintenance Mode & Ban enforcement middleware
    from bot.middlewares import AccessControlMiddleware
    access_mw = AccessControlMiddleware()
    dp.message.outer_middleware(access_mw)
    dp.callback_query.outer_middleware(access_mw)

    # Register all routers
    for router in get_all_routers():
        dp.include_router(router)

    # Start cleanup background task
    asyncio.create_task(cleanup_worker())

    # Start retention reminder worker
    asyncio.create_task(retention_worker(bot))

    # Start bot profile description worker (monthly active users count)
    asyncio.create_task(update_bot_description_worker(bot))

    # Set bot commands separately for regular users (no /admin) and admins (with /admin)
    try:
        from aiogram.types import (
            BotCommand, MenuButtonCommands,
            BotCommandScopeDefault, BotCommandScopeChat,
        )
        user_commands = [
            BotCommand(command="start", description="🏠 Bosh menyu / Главное меню"),
            BotCommand(command="vip", description="💎 VIP Obuna / VIP Подписка"),
            BotCommand(command="profile", description="👤 Profil / Профиль"),
        ]
        admin_commands = user_commands + [
            BotCommand(command="admin", description="🛠 Admin panel"),
        ]
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

        all_admins = set(ADMIN_IDS) | ({ADMIN_ID} if ADMIN_ID else set())
        for adm_id in all_admins:
            try:
                await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=adm_id))
            except Exception as adm_cmd_err:
                logger.warning(f"Could not set admin commands for {adm_id}: {adm_cmd_err}")

        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Bot commands scoped: /admin hidden from regular users, visible only to admins")
    except Exception as cmd_err:
        logger.warning(f"Could not set bot commands or menu button: {cmd_err}")

    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
