import unittest

from src.market.bybit_client import BybitMarketDataClient


class BybitMarketDataClientTests(unittest.TestCase):
    def test_supported_timeframes_include_fast_focused_pair_options(self) -> None:
        self.assertIn("1m", BybitMarketDataClient.SUPPORTED_TIMEFRAMES)
        self.assertIn("3m", BybitMarketDataClient.SUPPORTED_TIMEFRAMES)
        self.assertIn("5m", BybitMarketDataClient.SUPPORTED_TIMEFRAMES)

    def test_non_usdt_active_spot_market_is_allowed_for_ohlcv(self) -> None:
        market = {
            "spot": True,
            "active": True,
            "quote": "BTC",
        }

        self.assertTrue(BybitMarketDataClient._is_active_spot_market(market))
        self.assertFalse(
            BybitMarketDataClient._is_active_spot_usdt_market("ETH/BTC", market)
        )


if __name__ == "__main__":
    unittest.main()
