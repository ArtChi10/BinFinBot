from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class BotConfig:
    telegram_bot_token: str
    database_path: str


def load_config(env_path: str | Path = ".env") -> BotConfig:
    load_dotenv(env_path)

    token = getenv("TELEGRAM_BOT_TOKEN", "").strip()
    database_path = getenv("DATABASE_PATH", "bot.sqlite3").strip() or "bot.sqlite3"

    return BotConfig(
        telegram_bot_token=token,
        database_path=database_path,
    )
