from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import aiosqlite

from src.bot.database import ensure_user_settings, get_user_settings, init_db
from src.market.universes import PAIR_UNIVERSE_TOP_150


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = TemporaryDirectory()
        self.database_path = str(Path(self._temp_dir.name) / "test.sqlite3")

    async def asyncTearDown(self) -> None:
        self._temp_dir.cleanup()

    async def test_default_user_settings_use_top_150_pair_universe(self) -> None:
        await init_db(self.database_path)

        settings = await ensure_user_settings(self.database_path, telegram_user_id=123)

        self.assertEqual(settings.pair_universe, PAIR_UNIVERSE_TOP_150)

    async def test_init_db_migrates_existing_user_settings_table(self) -> None:
        await self._create_old_user_settings_table()

        await init_db(self.database_path)

        settings = await get_user_settings(self.database_path, telegram_user_id=123)

        self.assertIsNotNone(settings)
        self.assertEqual(settings.pair_universe, PAIR_UNIVERSE_TOP_150)

    async def _create_old_user_settings_table(self) -> None:
        async with aiosqlite.connect(self.database_path) as db:
            await db.execute(
                """
                CREATE TABLE user_settings (
                    telegram_user_id INTEGER PRIMARY KEY,
                    exchange TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    volume_change_percent REAL NOT NULL,
                    rsi_min INTEGER NOT NULL,
                    rsi_max INTEGER NOT NULL,
                    notifications_enabled INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await db.execute(
                """
                INSERT INTO user_settings (
                    telegram_user_id,
                    exchange,
                    timeframe,
                    volume_change_percent,
                    rsi_min,
                    rsi_max,
                    notifications_enabled
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (123, "bybit", "5m", 0.5, 30, 50, 1),
            )
            await db.commit()


if __name__ == "__main__":
    unittest.main()
