from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.bot.database import ensure_user_settings, get_user_settings, init_db
from src.bot.handlers import _activate_popular_30_universe
from src.market.universes import PAIR_UNIVERSE_POPULAR_30, PAIR_UNIVERSE_TOP_150


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = TemporaryDirectory()
        self.database_path = str(Path(self._temp_dir.name) / "test.sqlite3")
        await init_db(self.database_path)

    async def asyncTearDown(self) -> None:
        self._temp_dir.cleanup()

    async def test_popular_pair_editor_activates_popular_30_universe(self) -> None:
        settings = await ensure_user_settings(self.database_path, telegram_user_id=123)
        self.assertEqual(settings.pair_universe, PAIR_UNIVERSE_TOP_150)

        activated_settings = await _activate_popular_30_universe(
            self.database_path,
            telegram_user_id=123,
        )
        saved_settings = await get_user_settings(
            self.database_path,
            telegram_user_id=123,
        )

        self.assertEqual(activated_settings.pair_universe, PAIR_UNIVERSE_POPULAR_30)
        self.assertIsNotNone(saved_settings)
        self.assertEqual(saved_settings.pair_universe, PAIR_UNIVERSE_POPULAR_30)


if __name__ == "__main__":
    unittest.main()
