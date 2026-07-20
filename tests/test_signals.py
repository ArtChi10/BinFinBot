import unittest

from src.analysis.signals import evaluate_signal, format_signal_message


def make_candles(closes: list[float], volumes: list[float]) -> list[list[float]]:
    candles = []
    for index, (close, volume) in enumerate(zip(closes, volumes), start=1):
        candles.append(
            [
                index * 60_000,
                close - 1,
                close + 1,
                close - 2,
                close,
                volume,
            ]
        )
    return candles


class SignalTests(unittest.TestCase):
    def test_signal_matches_when_volume_and_rsi_match(self) -> None:
        candles = make_candles(
            closes=[float(value) for value in range(100, 116)],
            volumes=[1000] * 14 + [1000, 1010],
        )

        result = evaluate_signal(
            symbol="BTC/USDT",
            exchange="bybit",
            timeframe="15m",
            candles=candles,
            volume_threshold_percent=0.5,
            rsi_min=90,
            rsi_max=100,
        )

        self.assertTrue(result.matched)
        self.assertAlmostEqual(result.price_change_percent, 1 / 114 * 100)
        self.assertAlmostEqual(result.volume_change_percent, 1.0)
        self.assertEqual(result.price, 115)

    def test_signal_does_not_match_when_volume_is_below_threshold(self) -> None:
        candles = make_candles(
            closes=[float(value) for value in range(100, 116)],
            volumes=[1000] * 14 + [1000, 1004],
        )

        result = evaluate_signal(
            symbol="BTC/USDT",
            exchange="bybit",
            timeframe="15m",
            candles=candles,
            volume_threshold_percent=0.5,
            rsi_min=90,
            rsi_max=100,
        )

        self.assertFalse(result.matched)
        self.assertIn("below threshold", result.reason)

    def test_signal_does_not_match_when_rsi_is_outside_range(self) -> None:
        candles = make_candles(
            closes=[float(value) for value in range(100, 116)],
            volumes=[1000] * 14 + [1000, 1010],
        )

        result = evaluate_signal(
            symbol="BTC/USDT",
            exchange="bybit",
            timeframe="15m",
            candles=candles,
            volume_threshold_percent=0.5,
            rsi_min=30,
            rsi_max=50,
        )

        self.assertFalse(result.matched)
        self.assertIn("outside range", result.reason)

    def test_not_enough_candles_is_handled_without_crash(self) -> None:
        candles = make_candles(closes=[100], volumes=[1000])

        result = evaluate_signal(
            symbol="BTC/USDT",
            exchange="bybit",
            timeframe="15m",
            candles=candles,
            volume_threshold_percent=0.5,
            rsi_min=60,
            rsi_max=80,
        )

        self.assertFalse(result.matched)
        self.assertIn("Not enough candles", result.reason)

    def test_previous_zero_volume_is_handled_without_crash(self) -> None:
        candles = make_candles(
            closes=[float(value) for value in range(100, 116)],
            volumes=[1000] * 14 + [0, 1000],
        )

        result = evaluate_signal(
            symbol="BTC/USDT",
            exchange="bybit",
            timeframe="15m",
            candles=candles,
            volume_threshold_percent=0.5,
            rsi_min=60,
            rsi_max=80,
        )

        self.assertFalse(result.matched)
        self.assertIn("Previous volume", result.reason)

    def test_signal_message_formatter(self) -> None:
        candles = make_candles(
            closes=[float(value) for value in range(100, 116)],
            volumes=[1000] * 14 + [1000, 1010],
        )
        result = evaluate_signal(
            symbol="BTC/USDT",
            exchange="bybit",
            timeframe="15m",
            candles=candles,
            volume_threshold_percent=0.5,
            rsi_min=90,
            rsi_max=100,
        )

        message = format_signal_message(result)

        self.assertIn("Сигнал: BTC/USDT", message)
        self.assertIn("Биржа: Bybit", message)
        self.assertIn("Изменение цены: +0.88%", message)
        self.assertIn("Изменение объема: +1.00%", message)
        self.assertIn("Цена: 115 USDT", message)


if __name__ == "__main__":
    unittest.main()
