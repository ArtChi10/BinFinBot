from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.bot.config import load_config


class ConfigTests(unittest.TestCase):
    def test_database_path_is_used_as_local_fallback(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "TELEGRAM_BOT_TOKEN=test-token\n"
                "DATABASE_PATH=local.sqlite3\n",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True):
                config = load_config(env_path)

        self.assertEqual(config.telegram_bot_token, "test-token")
        self.assertEqual(config.database_url, "local.sqlite3")

    def test_database_url_takes_priority_over_database_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "TELEGRAM_BOT_TOKEN=test-token\n"
                "DATABASE_PATH=local.sqlite3\n"
                "DATABASE_URL=postgresql://user:password@localhost:5432/binfinbot\n",
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True):
                config = load_config(env_path)

        self.assertEqual(
            config.database_url,
            "postgresql://user:password@localhost:5432/binfinbot",
        )


if __name__ == "__main__":
    unittest.main()
