import asyncio
import logging
from contextlib import suppress

from aiohttp import ThreadedResolver
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from .config import load_config
from .database import init_db
from .handlers import router
from src.monitoring.monitor import run_market_monitor


def create_bot_session() -> AiohttpSession:
    session = AiohttpSession()
    session._connector_init["resolver"] = ThreadedResolver()
    return session


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    if not config.telegram_bot_token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it."
        )

    await init_db(config.database_path)

    bot = Bot(token=config.telegram_bot_token, session=create_bot_session())
    dispatcher = Dispatcher()
    dispatcher["database_path"] = config.database_path
    dispatcher.include_router(router)

    monitor_task: asyncio.Task[None] | None = None
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        monitor_task = asyncio.create_task(
            run_market_monitor(bot, config.database_path),
            name="market-monitor",
        )
        await dispatcher.start_polling(bot)
    finally:
        if monitor_task is not None:
            monitor_task.cancel()
            with suppress(asyncio.CancelledError):
                await monitor_task
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
