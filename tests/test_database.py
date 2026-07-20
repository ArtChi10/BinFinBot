from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import aiosqlite

from src.bot.database import (
    add_user_custom_pair,
    clear_user_custom_pairs,
    ensure_user_settings,
    get_selected_popular_pairs,
    get_user_custom_pairs,
    get_user_popular_pair_selections,
    get_user_settings,
    init_db,
    remove_user_custom_pair,
    set_all_user_popular_pair_selections,
    toggle_user_popular_pair_selection,
)
from src.market.universes import PAIR_UNIVERSE_TOP_150, POPULAR_30_USDT_PAIRS


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

    async def test_popular_pair_selections_default_to_all_selected(self) -> None:
        await init_db(self.database_path)
        await ensure_user_settings(self.database_path, telegram_user_id=123)

        selections = await get_user_popular_pair_selections(
            self.database_path,
            telegram_user_id=123,
        )
        selected_pairs = await get_selected_popular_pairs(
            self.database_path,
            telegram_user_id=123,
        )

        self.assertEqual(len(selections), 30)
        self.assertTrue(all(selections.values()))
        self.assertEqual(selected_pairs, list(POPULAR_30_USDT_PAIRS))

    async def test_popular_pair_selection_can_be_toggled(self) -> None:
        await init_db(self.database_path)
        await ensure_user_settings(self.database_path, telegram_user_id=123)

        selections = await toggle_user_popular_pair_selection(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
        )

        self.assertFalse(selections["BTC/USDT"])
        self.assertNotIn(
            "BTC/USDT",
            await get_selected_popular_pairs(self.database_path, telegram_user_id=123),
        )

    async def test_all_popular_pair_selections_can_be_cleared(self) -> None:
        await init_db(self.database_path)
        await ensure_user_settings(self.database_path, telegram_user_id=123)

        selections = await set_all_user_popular_pair_selections(
            self.database_path,
            telegram_user_id=123,
            selected=False,
        )

        self.assertFalse(any(selections.values()))
        self.assertEqual(
            await get_selected_popular_pairs(self.database_path, telegram_user_id=123),
            [],
        )

    async def test_custom_pairs_can_be_added_and_normalized(self) -> None:
        await init_db(self.database_path)

        custom_pairs = await add_user_custom_pair(
            self.database_path,
            telegram_user_id=123,
            symbol="eth btc",
        )

        self.assertEqual(custom_pairs, ["ETH/BTC"])
        self.assertEqual(
            await get_user_custom_pairs(self.database_path, telegram_user_id=123),
            ["ETH/BTC"],
        )

    async def test_custom_pairs_can_be_removed_and_cleared(self) -> None:
        await init_db(self.database_path)
        await add_user_custom_pair(
            self.database_path,
            telegram_user_id=123,
            symbol="ETH/BTC",
        )
        await add_user_custom_pair(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDC",
        )

        custom_pairs = await remove_user_custom_pair(
            self.database_path,
            telegram_user_id=123,
            symbol="eth-btc",
        )
        cleared_pairs = await clear_user_custom_pairs(
            self.database_path,
            telegram_user_id=123,
        )

        self.assertEqual(custom_pairs, ["BTC/USDC"])
        self.assertEqual(cleared_pairs, [])

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
