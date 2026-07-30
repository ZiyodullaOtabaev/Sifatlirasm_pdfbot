"""
Bot entry point — aiogram 3.x dispatcher setup and polling.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
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

    # Register all routers
    for router in get_all_routers():
        dp.include_router(router)

    # Start cleanup background task
    asyncio.create_task(cleanup_worker())

    # Start retention reminder worker
    asyncio.create_task(retention_worker(bot))

    # Start bot profile description worker (monthly active users count)
    asyncio.create_task(update_bot_description_worker(bot))

    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
