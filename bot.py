import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import start, student_flow, admin
from database.db import init_db
import config

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


async def main():
    # Validate token
    if not config.BOT_TOKEN or config.BOT_TOKEN.startswith("PUT_"):
        log.error("=" * 50)
        log.error("BOT_TOKEN is not set in .env file!")
        log.error("Open .env and replace PUT_YOUR_BOT_TOKEN_HERE")
        log.error("=" * 50)
        return

    log.info("Initializing database...")
    await init_db()
    log.info("Database ready.")

    bot = Bot(token=config.BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(student_flow.router)
    dp.include_router(admin.router)

    # Print startup info
    bot_info = await bot.get_me()
    log.info("=" * 50)
    log.info(f"Bot started: @{bot_info.username}")
    log.info(f"Bot name:    {bot_info.full_name}")
    log.info(f"Admin ID:    {config.ADMIN_ID}")
    log.info("=" * 50)
    log.info("Listening for messages... (Ctrl+C to stop)")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        log.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
