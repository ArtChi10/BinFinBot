import unittest

from src.bot.database import UserSettings
from src.market.universes import (
    PAIR_UNIVERSE_POPULAR_30,
    PAIR_UNIVERSE_TOP_150,
    POPULAR_30_USDT_PAIRS,
)
from src.monitoring.monitor import _symbols_by_pair_universe, closed_ohlcv_candles


class MonitoringTests(unittest.TestCase):
    def test_closed_ohlcv_candles_excludes_open_candle(self) -> None:
        candles = [
            [0, 1, 1, 1, 1, 100],
            [300_000, 1, 1, 1, 1, 100],
            [600_000, 1, 1, 1, 1, 100],
        ]

        result = closed_ohlcv_candles(candles, timeframe="5m", now_ms=899_999)

        self.assertEqual(result, candles[:2])

    def test_closed_ohlcv_candles_keeps_candle_at_close_time(self) -> None:
        candles = [
            [0, 1, 1, 1, 1, 100],
            [300_000, 1, 1, 1, 1, 100],
        ]

        result = closed_ohlcv_candles(candles, timeframe="5m", now_ms=600_000)

        self.assertEqual(result, candles)

    def test_closed_ohlcv_candles_rejects_unknown_timeframe(self) -> None:
        with self.assertRaises(ValueError):
            closed_ohlcv_candles([], timeframe="1h", now_ms=0)

    def test_popular_30_universe_contains_30_usdt_pairs(self) -> None:
        self.assertEqual(len(POPULAR_30_USDT_PAIRS), 30)
        self.assertTrue(all(symbol.endswith("/USDT") for symbol in POPULAR_30_USDT_PAIRS))

    def test_symbols_by_pair_universe_resolves_dynamic_and_fixed_lists(self) -> None:
        top_user = _settings(telegram_user_id=1, pair_universe=PAIR_UNIVERSE_TOP_150)
        popular_user = _settings(
            telegram_user_id=2,
            pair_universe=PAIR_UNIVERSE_POPULAR_30,
        )
        top_pairs = ["BTC/USDT", "ETH/USDT"]

        result = _symbols_by_pair_universe([top_user, popular_user], top_pairs)

        self.assertEqual(result[PAIR_UNIVERSE_TOP_150], top_pairs)
        self.assertEqual(result[PAIR_UNIVERSE_POPULAR_30], list(POPULAR_30_USDT_PAIRS))


def _settings(telegram_user_id: int, pair_universe: str) -> UserSettings:
    return UserSettings(
        telegram_user_id=telegram_user_id,
        exchange="bybit",
        pair_universe=pair_universe,
        timeframe="5m",
        volume_change_percent=0.5,
        rsi_min=30,
        rsi_max=50,
        notifications_enabled=True,
        created_at="2026-01-01 00:00:00",
        updated_at="2026-01-01 00:00:00",
    )


if __name__ == "__main__":
    unittest.main()
