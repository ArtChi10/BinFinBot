from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import ccxt.async_support as ccxt


class MarketDataError(RuntimeError):
    """Raised when market data cannot be loaded or normalized."""


class UnsupportedTimeframeError(ValueError):
    """Raised when a requested timeframe is not part of the MVP."""


class BybitMarketDataClient:
    SUPPORTED_TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m"}

    def __init__(self) -> None:
        self._exchange = ccxt.bybit(
            {
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                },
            }
        )

    async def __aenter__(self) -> BybitMarketDataClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._exchange.close()
        session = getattr(self._exchange, "session", None)
        if session is not None and not session.closed:
            await session.close()
        self._exchange.session = None

    async def get_top_usdt_pairs(self, limit: int = 150) -> list[str]:
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")

        try:
            markets = await self._exchange.load_markets()
            tickers = await self._exchange.fetch_tickers()
        except ccxt.NetworkError as exc:
            raise MarketDataError(f"Network error while loading Bybit markets: {exc}") from exc
        except ccxt.ExchangeError as exc:
            raise MarketDataError(f"Bybit exchange error while loading markets: {exc}") from exc
        except ccxt.BaseError as exc:
            raise MarketDataError(f"ccxt error while loading Bybit markets: {exc}") from exc

        ranked_pairs: list[tuple[str, float]] = []
        for symbol, market in markets.items():
            if not self._is_active_spot_usdt_market(symbol, market):
                continue

            ticker = tickers.get(symbol)
            quote_volume = self._quote_volume(ticker)
            if quote_volume is None:
                continue

            ranked_pairs.append((symbol, quote_volume))

        if not ranked_pairs:
            raise MarketDataError(
                "Bybit returned no active spot /USDT markets with 24h quote volume."
            )

        ranked_pairs.sort(key=lambda pair: pair[1], reverse=True)
        return [symbol for symbol, _ in ranked_pairs[:limit]]

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> list[list[float]]:
        if timeframe not in self.SUPPORTED_TIMEFRAMES:
            supported = ", ".join(sorted(self.SUPPORTED_TIMEFRAMES))
            raise UnsupportedTimeframeError(
                f"Unsupported timeframe '{timeframe}'. Supported values: {supported}."
            )
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")

        try:
            markets = await self._exchange.load_markets()
            market = markets.get(symbol)
            if not self._is_active_spot_market(market):
                raise MarketDataError(
                    f"Symbol '{symbol}' is not an active Bybit spot market."
                )

            candles = await self._exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=limit,
            )
        except MarketDataError:
            raise
        except ccxt.NetworkError as exc:
            raise MarketDataError(
                f"Network error while loading OHLCV for {symbol} {timeframe}: {exc}"
            ) from exc
        except ccxt.ExchangeError as exc:
            raise MarketDataError(
                f"Bybit exchange error while loading OHLCV for {symbol} {timeframe}: {exc}"
            ) from exc
        except ccxt.BaseError as exc:
            raise MarketDataError(
                f"ccxt error while loading OHLCV for {symbol} {timeframe}: {exc}"
            ) from exc

        if not candles:
            raise MarketDataError(f"Bybit returned no OHLCV candles for {symbol}.")

        normalized_candles: list[list[float]] = []
        for candle in candles:
            if len(candle) < 6:
                raise MarketDataError(f"Unexpected OHLCV candle format: {candle!r}.")
            normalized_candles.append([float(value) for value in candle[:6]])

        return normalized_candles

    @staticmethod
    def _is_active_spot_usdt_market(
        symbol: str,
        market: Mapping[str, Any] | None,
    ) -> bool:
        return (
            symbol.endswith("/USDT")
            and BybitMarketDataClient._is_active_spot_market(market)
            and market is not None
            and market.get("quote") == "USDT"
        )

    @staticmethod
    def _is_active_spot_market(
        market: Mapping[str, Any] | None,
    ) -> bool:
        if market is None:
            return False
        return (
            market.get("spot") is True
            and market.get("active") is True
        )

    @staticmethod
    def _quote_volume(ticker: Mapping[str, Any] | None) -> float | None:
        if ticker is None:
            return None

        quote_volume = ticker.get("quoteVolume")
        if quote_volume is None:
            info = ticker.get("info") or {}
            quote_volume = (
                info.get("turnover24h")
                or info.get("quoteVolume")
                or info.get("quote_volume")
            )

        if quote_volume is None:
            return None

        try:
            return float(quote_volume)
        except (TypeError, ValueError):
            return None
