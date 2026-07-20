import unittest

from src.analysis.indicators import (
    calculate_price_change_percent,
    calculate_rsi,
    calculate_volume_change_percent,
)


class IndicatorTests(unittest.TestCase):
    def test_volume_change_percent_uses_expected_formula(self) -> None:
        result = calculate_volume_change_percent(
            current_volume=100.5,
            previous_volume=100,
        )

        self.assertAlmostEqual(result, 0.5)

    def test_volume_change_percent_returns_none_for_zero_previous_volume(self) -> None:
        self.assertIsNone(
            calculate_volume_change_percent(
                current_volume=100,
                previous_volume=0,
            )
        )

    def test_price_change_percent_uses_expected_formula(self) -> None:
        result = calculate_price_change_percent(
            current_price=105,
            previous_price=100,
        )

        self.assertAlmostEqual(result, 5.0)

    def test_price_change_percent_returns_none_for_zero_previous_price(self) -> None:
        self.assertIsNone(
            calculate_price_change_percent(
                current_price=100,
                previous_price=0,
            )
        )

    def test_rsi_returns_number_for_enough_closes(self) -> None:
        closes = [float(value) for value in range(1, 21)]

        result = calculate_rsi(closes)

        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 100)

    def test_rsi_returns_none_for_not_enough_closes(self) -> None:
        closes = [float(value) for value in range(1, 14)]

        self.assertIsNone(calculate_rsi(closes))


if __name__ == "__main__":
    unittest.main()
