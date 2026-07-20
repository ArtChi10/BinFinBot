import unittest

from src.monitoring.monitor import closed_ohlcv_candles


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


if __name__ == "__main__":
    unittest.main()
