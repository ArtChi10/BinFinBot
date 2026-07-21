from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.bot.database import init_db
from src.monitoring.cooldown import (
    can_send_signal,
    cooldown_seconds_for_timeframe,
    get_last_signal_sent_at,
    record_signal_sent,
)


class CooldownTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = TemporaryDirectory()
        self.database_path = str(Path(self._temp_dir.name) / "test.sqlite3")
        await init_db(self.database_path)

    async def asyncTearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_cooldown_seconds_follow_timeframe(self) -> None:
        self.assertEqual(cooldown_seconds_for_timeframe("1m"), 60)
        self.assertEqual(cooldown_seconds_for_timeframe("3m"), 180)
        self.assertEqual(cooldown_seconds_for_timeframe("5m"), 300)
        self.assertEqual(cooldown_seconds_for_timeframe("15m"), 900)
        self.assertEqual(cooldown_seconds_for_timeframe("30m"), 1800)

    def test_unknown_timeframe_raises(self) -> None:
        with self.assertRaises(ValueError):
            cooldown_seconds_for_timeframe("1h")

    async def test_can_send_when_no_previous_signal_exists(self) -> None:
        allowed = await can_send_signal(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
            timeframe="15m",
            now=datetime(2026, 1, 1, tzinfo=UTC),
        )

        self.assertTrue(allowed)

    async def test_cooldown_blocks_repeated_signal(self) -> None:
        sent_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        await record_signal_sent(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
            timeframe="15m",
            sent_at=sent_at,
        )

        allowed = await can_send_signal(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
            timeframe="15m",
            now=sent_at + timedelta(minutes=14, seconds=59),
        )

        self.assertFalse(allowed)

    async def test_cooldown_allows_after_timeframe_passes(self) -> None:
        sent_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        await record_signal_sent(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
            timeframe="15m",
            sent_at=sent_at,
        )

        allowed = await can_send_signal(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
            timeframe="15m",
            now=sent_at + timedelta(minutes=15),
        )

        self.assertTrue(allowed)

    async def test_record_signal_sent_updates_existing_row(self) -> None:
        first_sent_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        second_sent_at = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)

        await record_signal_sent(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
            timeframe="15m",
            sent_at=first_sent_at,
        )
        await record_signal_sent(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
            timeframe="15m",
            sent_at=second_sent_at,
        )

        last_sent_at = await get_last_signal_sent_at(
            self.database_path,
            telegram_user_id=123,
            symbol="BTC/USDT",
            timeframe="15m",
        )

        self.assertEqual(last_sent_at, second_sent_at)


if __name__ == "__main__":
    unittest.main()
