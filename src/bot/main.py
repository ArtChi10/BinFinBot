import asyncio
import logging

from aiogram import Bot, Dispatcher

from .config import load_config
from .database import init_db
from .handlers import router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    if not config.telegram_bot_token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it."
        )

    await init_db(config.database_path)

    bot = Bot(token=config.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher["database_path"] = config.database_path
    dispatcher.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
